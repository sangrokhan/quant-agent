"""Strategy: Mulvaney-replica long-term Donchian breakout with midline
trailing stop (Concretum Research reverse-engineering of Paul Mulvaney's
CTA trend model).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-023):
Per Concretum Research's reverse-engineering of Paul Mulvaney Capital
Management's systematic trend-following approach (summarized at
https://the7circles.uk/trade-like-mulvaney/, read via `browser_exec` after
the direct Substack article proved paywalled/inaccessible in a prior
iteration): fitting 4,320 synthetic CTA trend programs against MCM's
monthly returns (R^2 0.71-0.73) found the best-fit configuration uses:
  - A canonical Donchian channel breakout entry (new N-day high => long)
    with a 126-trading-day (~6 calendar month) lookback -- matching
    Mulvaney's own stated average holding period of ~6 months.
  - The Donchian channel MIDLINE (average of the rolling high/low) as the
    trailing stop/exit once in a position -- this widens automatically as
    volatility/range expands, without a separate ATR-multiplier parameter.
  - An INITIAL stop offset by one-third of the Donchian channel's range
    from the entry price (tighter than the midline early in the trade,
    consistent with Mulvaney's own description of tighter initial risk
    thresholds that loosen as the position develops).

This repo has extensively tested Donchian breakout/midline-pullback/
midline-slope variants (2026-09-08-017, 2026-09-10-069, 2026-09-10-123,
2026-09-18-004), but never this specific LONG-TERM (126-day) breakout
construction with a midline TRAILING STOP as the exit mechanism (as
opposed to entry filters, pullback-to-midline mean reversion, or midline
SLOPE as a separate signal) -- a genuinely distinct trend-following system
architecture directly reverse-engineered from a real, still-operating CTA.

Signal logic
------------
- donchian_window (default 126) trading days for the rolling high/low.
- Entry (long): close makes a fresh donchian_window-day high (breaks above
  the prior period's rolling max).
- Initial stop: entry_price - initial_stop_frac (default 1/3) * the
  Donchian channel range (high-low) AT ENTRY.
- Once in position, the stop trails to max(initial_stop_level, rolling
  Donchian midline) -- i.e. widens toward (and eventually is superseded
  by) the midline as the position ages, but never below the fixed initial
  stop level (a ratchet, consistent with Mulvaney's own description that
  stops "move only in the direction of the trade").
- Exit: close falls below the current trailing stop level, or a
  max_hold_days backstop (default 252, ~1yr, generously wide since
  Mulvaney's average hold is ~6mo and this repo's other long-hold trend
  strategies use similarly wide backstops).
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
    donchian_window: int = 126,
    initial_stop_frac: float = 1.0 / 3.0,
    max_hold_days: int = 252,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close
    n = len(close)

    rolling_high = high.rolling(donchian_window).max()
    rolling_low = low.rolling(donchian_window).min()
    midline = (rolling_high + rolling_low) / 2.0

    # Fresh breakout: close exceeds the PRIOR period's rolling high (shift
    # by 1 to avoid using today's own high in today's own breakout check).
    prior_high = rolling_high.shift(1)
    breakout = close > prior_high

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_level = None

    for i in range(n):
        if in_position:
            held = i - entry_idx
            current_midline = midline.iloc[i]
            if current_midline is not None and current_midline == current_midline:  # not NaN
                # Ratchet: stop only ever moves up (toward/with the
                # midline), never back down toward the initial fixed level.
                stop_level = max(stop_level, current_midline)
            price_now = close.iloc[i]
            if price_now < stop_level or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                stop_level = None
                continue
            position.iloc[i] = 1
        else:
            if bool(breakout.iloc[i]) and rolling_high.iloc[i] == rolling_high.iloc[i] and rolling_low.iloc[i] == rolling_low.iloc[i]:
                in_position = True
                entry_idx = i
                entry_price = close.iloc[i]
                channel_range = rolling_high.iloc[i] - rolling_low.iloc[i]
                stop_level = entry_price - initial_stop_frac * channel_range
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
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
