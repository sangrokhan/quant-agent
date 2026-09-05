"""Strategy: Ichimoku Kumo (cloud) breakout trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-049):
Price breaking above the Ichimoku Kumo (the cloud spanning between Senkou
Span A and Senkou Span B) signals a fresh, confirmed uptrend worth being
long in, since the cloud represents a consolidated support/resistance
zone built from prior price structure; a breakout above it indicates
buyers have overwhelmed that resistance band. This is the "Kumo Breakout"
strategy per TrendSpider's Ichimoku Cloud Trading Strategies article
(https://trendspider.com/learning-center/ichimoku-cloud-trading-strategies/),
distinct from the previously-tested Tenkan/Kijun-cross + cloud-confirmation
variant (2026-09-04-034, near-miss rejected) -- here the ONLY trigger is
price crossing the cloud boundary itself, no separate momentum-line cross
required.

Signal logic
------------
- Tenkan-sen (conversion line): midpoint of highest-high/lowest-low over
  `tenkan_window` bars (default 9).
- Kijun-sen (base line): midpoint of highest-high/lowest-low over
  `kijun_window` bars (default 26).
- Senkou Span A: average of Tenkan-sen and Kijun-sen, projected forward
  `displacement` bars (default 26) -- standard Ichimoku convention.
- Senkou Span B: midpoint of highest-high/lowest-low over `senkou_b_window`
  bars (default 52), also projected forward `displacement` bars.
- Kumo (cloud) upper/lower bound at time t = max/min(Senkou Span A[t],
  Senkou Span B[t]) using the values already projected onto t (i.e. no
  look-ahead -- at any bar t we only use spans that were computed and
  displaced using data available strictly before t).
- Entry (long): close crosses from at-or-below the upper Kumo boundary to
  strictly above it (bullish Kumo breakout).
- Exit: close crosses back below the lower Kumo boundary (bearish
  breakdown), OR after a `max_hold_days` time-stop (avoid indefinite
  holds through a stagnant cloud).
- Flat (no position) at all other times.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _donchian_mid(high: pd.Series, low: pd.Series, window: int) -> pd.Series:
    return (high.rolling(window).max() + low.rolling(window).min()) / 2.0


def generate_signals(
    price_df: pd.DataFrame,
    tenkan_window: int = 9,
    kijun_window: int = 26,
    senkou_b_window: int = 52,
    displacement: int = 26,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tenkan = _donchian_mid(high, low, tenkan_window)
    kijun = _donchian_mid(high, low, kijun_window)
    senkou_a_raw = (tenkan + kijun) / 2.0
    senkou_b_raw = _donchian_mid(high, low, senkou_b_window)

    # Standard Ichimoku projects the spans forward `displacement` bars so
    # that, viewed on the chart, the cloud sits ahead of price. To use the
    # cloud as a *current* support/resistance boundary without look-ahead,
    # shift the already-computed spans forward by `displacement` bars --
    # this means the cloud boundary active "today" was computed using data
    # from `displacement` bars ago, exactly matching how a chart reader
    # would see it.
    senkou_a = senkou_a_raw.shift(displacement)
    senkou_b = senkou_b_raw.shift(displacement)

    kumo_upper = pd.concat([senkou_a, senkou_b], axis=1).max(axis=1)
    kumo_lower = pd.concat([senkou_a, senkou_b], axis=1).min(axis=1)

    bullish_breakout = (close > kumo_upper) & (close.shift(1) <= kumo_upper.shift(1))
    bearish_breakdown = (close < kumo_lower) & (close.shift(1) >= kumo_lower.shift(1))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_count = 0

    valid_start = kumo_upper.first_valid_index()

    for ts in close.index:
        if valid_start is None or ts < valid_start:
            position.loc[ts] = 0
            continue

        if in_position:
            hold_count += 1
            if bool(bearish_breakdown.loc[ts]) or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                position.loc[ts] = 0
                continue
            position.loc[ts] = 1
        else:
            if bool(bullish_breakout.loc[ts]):
                in_position = True
                hold_count = 0
                position.loc[ts] = 1
            else:
                position.loc[ts] = 0

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Position-weighted daily returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **params)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
