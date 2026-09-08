"""Strategy: single-asset McClellan-Oscillator-style breadth-proxy mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-172):
Per QuantifiedStrategies.com "McClellan Oscillator and Summation Index:
Trading Strategy and Backtest Analysis"
(https://www.quantifiedstrategies.com/mcclellan-oscillator-and-summation-index/,
retrieved via browser fallback -- web_extract failed with a DuckDuckGo
backend error), the classic McClellan Oscillator is the difference between a
19-day EMA and a 39-day EMA of the daily advances-minus-declines breadth
series; the source's own simple backtest rule is: go long when the
oscillator crosses below -100 (deeply oversold breadth), exit/sell when it
crosses back above +100.

This repo's data/loaders.py only provides single-symbol OHLCV (no market-wide
advance/decline breadth feed), so the true McClellan Oscillator cannot be
computed directly. We adapt it as a single-asset "own-breadth" proxy: instead
of counting advancing/declining stocks market-wide, we use the daily sign of
the asset's own price change (+1 up day / -1 down day / 0 flat) as a
single-name breadth analog, then apply the identical 19/39-day EMA-difference
construction. Because raw levels of a count-based oscillator (-100/+100 on
~2800 Nasdaq names) don't translate to a +/-1 sign series, we normalize the
proxy oscillator via a rolling percentile rank (same normalization pattern
already used elsewhere in this repo for other regime/percentile gates) and
threshold on percentile extremes instead of raw +/-100 levels -- preserving
the source's own oversold-long / overbought-exit polarity structure.

First McClellan-family (breadth-thrust EMA-difference oscillator) entry in
this repo; mechanically distinct from all prior RSI/CCI/Stochastic-style
bounded oscillators (those normalize price level or momentum magnitude
directly, not the EMA-smoothed difference of a +/-1 daily direction series)
and from the correlation-ratio regime gate (2026-09-08-152, which uses a
cross-asset basket, not this asset's own signed-direction series).

Signal logic
------------
- daily_dir = sign of daily price change (+1/-1/0).
- mcclellan_proxy = EMA(daily_dir, ema_fast) - EMA(daily_dir, ema_slow).
- pct_rank = rolling percentile rank of mcclellan_proxy over trailing
  `lookback` days (own history, no external asset needed).
- Entry (long): pct_rank crosses below `oversold_pct` (deeply negative
  breadth-proxy reading relative to its own recent history).
- Exit: pct_rank crosses back above `overbought_pct`, OR a max holding
  period of `max_hold_days` trading days is reached.

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


def generate_signals(
    price_df: pd.DataFrame,
    ema_fast: int = 19,
    ema_slow: int = 39,
    lookback: int = 252,
    oversold_pct: float = 0.1,
    overbought_pct: float = 0.9,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    daily_change = close.diff()
    daily_dir = daily_change.apply(lambda x: 1.0 if x > 0 else (-1.0 if x < 0 else 0.0))

    ema_f = daily_dir.ewm(span=ema_fast, adjust=False).mean()
    ema_s = daily_dir.ewm(span=ema_slow, adjust=False).mean()
    mcclellan_proxy = ema_f - ema_s

    pct_rank = mcclellan_proxy.rolling(lookback, min_periods=ema_slow).apply(
        lambda x: (x < x[-1]).sum() / len(x), raw=True
    )

    entry = pct_rank < oversold_pct
    exit_signal = pct_rank > overbought_pct

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
