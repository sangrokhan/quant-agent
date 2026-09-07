"""Strategy: Outside Day continuation breakout, long-only, trend-filtered.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-086),
sourced from https://www.thepatternsite.com/OutsideDays.html (Thomas
Bulkowski's "Outside Days Chart Pattern" statistics page). Concrete rules
quoted from the source:

    "Look for a higher high and lower low on the second day. The price bar
    fits outside the prior day's range." (2-bar outside-day definition)

    "The pattern acts as a continuation 63% of the time (bull market,
    upward breakout)." / "Trade with the trend: Since outside days act as
    continuation patterns, expect the breakout to be in the same direction
    as the inbound price trend."

    "A breakout occurs when the stock closes either above the top of the
    pattern or below the bottom of it."

Operationalized: within an established uptrend (close > SMA(trend_window),
Bulkowski's own trend definition proxy), a 2-bar outside day (day t's high
> day t-1's high AND day t's low < day t-1's low, day t-1 not a 4-price
doji) forms the pattern; long entry when a SUBSEQUENT close breaks above
the outside day's own high (the "top of the pattern") within
breakout_expiry_bars, trading WITH the established uptrend per the
source's own "trade with the trend" tactic (only upward breakouts taken,
matching the source's disclosed 63% continuation rate figure, not the
reversal case). Exit when close falls back below the SMA trend filter or a
max_hold_days time-stop.

Distinct from the already-tested "inside day immediately followed by
outside day" 2-bar-sequence strategy (2026-09-07-008, DIA-specific,
requires an ADDITIONAL inside-day precondition) -- here the outside day
alone (no inside-day precondition) is the pattern, matching Bulkowski's own
broader/simpler definition and his own explicit continuation-with-trend
trading tactic.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    breakout_expiry_bars: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    sma = close.rolling(trend_window).mean()
    uptrend = close > sma

    prior_high = high.shift(1)
    prior_low = low.shift(1)
    prior_is_doji = (high.shift(1) == low.shift(1))
    is_outside_day = (high > prior_high) & (low < prior_low) & (~prior_is_doji.fillna(False))

    n = len(df)
    outside_day_idx = np.where(is_outside_day.fillna(False).values)[0]

    entries = np.zeros(n, dtype=bool)
    high_vals = high.values
    close_vals = close.values
    uptrend_vals = uptrend.fillna(False).values

    for i2 in outside_day_idx:
        if not uptrend_vals[i2]:
            continue  # only trade continuation breakouts WITH the established uptrend
        pattern_top = high_vals[i2]
        for t in range(i2 + 1, min(i2 + 1 + breakout_expiry_bars, n)):
            if close_vals[t] > pattern_top:
                entries[t] = True
                break

    position = np.zeros(n, dtype=int)
    in_pos = False
    entry_bar = -1
    for t in range(n):
        if entries[t] and not in_pos:
            in_pos = True
            entry_bar = t
        if in_pos:
            position[t] = 1
            held = t - entry_bar
            trend_broken = not uptrend_vals[t] if not pd.isna(uptrend.iloc[t]) else False
            if trend_broken or held >= max_hold_days:
                in_pos = False

    return pd.Series(position, index=close.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
