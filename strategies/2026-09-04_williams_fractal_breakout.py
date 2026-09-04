"""Strategy: Bill Williams Fractal swing-point breakout with trailing fractal stop.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-134):
Per theindicatorlab.com's Fractals_Bill_Williams review, a "fractal" is a
5-bar swing pattern: a fractal low is a bar whose low is lower than the
`left_bars` bars before it and `right_bars` bars after it (default 2/2,
confirmed with a `right_bars`-bar lag since you need the following bars to
know it held); a fractal high is the mirror (highest high vs neighbors).
The source's own systematic rule: after a fractal low forms, wait for a
later close to break above the most recently confirmed fractal high --
that's the long entry (a pullback-reversal-continuation setup in a trend).
Exit/trailing stop: trail behind the most recently confirmed fractal low;
exit when close breaks back below it. This is the first Fractal-family
indicator tested in this repo (distinct from all momentum-oscillator /
moving-average-cross variants tried so far -- it's a raw price-structure
swing-point breakout+trailing-stop system with no oscillator/MA math at
all).

Signal logic
------------
- fractal_low[i]  = low[i]  is the minimum of low[i-left_bars : i+right_bars+1]
- fractal_high[i] = high[i] is the maximum of high[i-left_bars : i+right_bars+1]
  (both only knowable `right_bars` bars later -- shifted forward by
  right_bars before use, to avoid look-ahead bias)
- Maintain the most recently confirmed fractal_high level and fractal_low
  level as of each bar (forward-filled).
- Entry (long): flat, and close crosses above the most recently confirmed
  fractal_high level (a fresh cross, not just "is above").
- Exit: in position, and close crosses below the most recently confirmed
  fractal_low level (trailing-stop-style exit using the latest swing low),
  OR a max_hold_days time-stop as a safety backstop (source doesn't specify
  one, but exit-only-on-mirror-fractal can hold indefinitely in a strong
  trend with no low ever printing -- degenerate on illiquid data, so add a
  generous backstop).
- Long-only, flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _confirmed_fractals(df: pd.DataFrame, left_bars: int, right_bars: int):
    high = df["high"]
    low = df["low"]
    n = len(df)

    is_fractal_high = pd.Series(False, index=df.index)
    is_fractal_low = pd.Series(False, index=df.index)

    for i in range(left_bars, n - right_bars):
        window_high = high.iloc[i - left_bars: i + right_bars + 1]
        window_low = low.iloc[i - left_bars: i + right_bars + 1]
        if high.iloc[i] == window_high.max():
            is_fractal_high.iloc[i] = True
        if low.iloc[i] == window_low.min():
            is_fractal_low.iloc[i] = True

    # A fractal at bar i is only *confirmed* (knowable without look-ahead)
    # once we've observed the right_bars bars after it -> shift forward.
    confirmed_high_level = pd.Series(index=df.index, dtype=float)
    confirmed_low_level = pd.Series(index=df.index, dtype=float)
    confirmed_high_level[is_fractal_high] = high[is_fractal_high]
    confirmed_low_level[is_fractal_low] = low[is_fractal_low]
    confirmed_high_level = confirmed_high_level.shift(right_bars)
    confirmed_low_level = confirmed_low_level.shift(right_bars)

    # Forward-fill so every bar carries the most recently confirmed level.
    last_fractal_high = confirmed_high_level.ffill()
    last_fractal_low = confirmed_low_level.ffill()
    return last_fractal_high, last_fractal_low


def generate_signals(
    price_df: pd.DataFrame,
    left_bars: int = 2,
    right_bars: int = 2,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(df)

    last_fractal_high, last_fractal_low = _confirmed_fractals(df, left_bars, right_bars)

    close_prev = close.shift(1)
    high_prev = last_fractal_high.shift(1)
    low_prev = last_fractal_low.shift(1)

    entry_trigger = (close > last_fractal_high) & (close_prev <= high_prev)
    exit_trigger = (close < last_fractal_low) & (close_prev >= low_prev)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            et = bool(exit_trigger.iloc[i]) if pd.notna(exit_trigger.iloc[i]) else False
            if et or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            entered = bool(entry_trigger.iloc[i]) if pd.notna(entry_trigger.iloc[i]) else False
            if entered:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    left_bars: int = 2,
    right_bars: int = 2,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df, left_bars=left_bars, right_bars=right_bars, max_hold_days=max_hold_days
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
