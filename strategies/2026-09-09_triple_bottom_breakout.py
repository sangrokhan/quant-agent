"""Strategy: Triple Bottom reversal breakout (long-only).

Hypothesis (this iteration):
Per Bulkowski's ThePatternSite.com (via Google SERP snippets: "Triple
bottoms are chart patterns with three valleys near the same price...
[with] the highest peak between the three bottoms" acting as the
confirmation/breakout level, and "Place a stop a few pennies below the
most recent low"), a Triple Bottom is three minor swing lows occurring at
approximately the same price level (within a tolerance), separated by
two intermediate rebound peaks. The pattern confirms as a genuine
reversal (not just a random 3-touch support test) when price breaks
above the higher of the two intermediate peaks between the bottoms.

Distinct from the already-tested Double Bottom (2026-09-08-101,
rejected, a 2-valley W-pattern with a single neckline) via the THIRD
valley requirement -- a third successful test-and-hold of the same
support level is, per the behavioral reversal literature already cited
elsewhere in this repo (double-bottom, Turtle Soup), a stronger signal
of exhausted selling pressure than a single retest. First Triple Bottom
(3-valley reversal) chart pattern tested in this repo.

Signal logic
------------
- Identify local swing lows: a bar is a swing low if its close is the
  minimum close within a +/- pivot_window bar window.
- Three consecutive confirmed swing lows (bottom1, bottom2, bottom3) are
  a valid Triple Bottom if:
  - all three lows are within bottom_tolerance_pct of each other
    (source's "near the same price" criterion);
  - there are two distinct intermediate local swing HIGHS between
    bottom1-bottom2 and bottom2-bottom3 (the rebound peaks);
  - the pattern isn't too compressed: bottom3 occurs at least
    min_pattern_bars after bottom1.
- Entry (long): close breaks above the HIGHER of the two intermediate
  peaks (source's own confirmation level) within confirm_window bars
  after bottom3 forms.
- Exit: close crosses below bottom3's own low (source's stop-loss rule:
  "a few pennies below the most recent low"), a measured-move target
  (entry_price + reward_mult*(confirmation_level - bottom3_low)), or a
  max_hold_days time-stop.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

Sources:
    https://thepatternsite.com (Bulkowski, via Google SERP snippets --
    direct page fetch 404'd this session)
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
    pivot_window: int = 5,
    bottom_tolerance_pct: float = 0.02,
    min_pattern_bars: int = 15,
    max_pattern_bars: int = 120,
    confirm_window: int = 20,
    reward_mult: float = 1.5,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)
    c = close.to_numpy(dtype=float)

    is_swing_low = np.zeros(n, dtype=bool)
    is_swing_high = np.zeros(n, dtype=bool)
    for i in range(pivot_window, n - pivot_window):
        window = c[i - pivot_window:i + pivot_window + 1]
        if c[i] == window.min() and np.argmin(window) == pivot_window:
            is_swing_low[i] = True
        if c[i] == window.max() and np.argmax(window) == pivot_window:
            is_swing_high[i] = True

    swing_low_idx = np.where(is_swing_low)[0]
    swing_high_idx = np.where(is_swing_high)[0]

    entry_cond = np.zeros(n, dtype=bool)
    confirm_level_at = np.full(n, np.nan)
    bottom3_low_at = np.full(n, np.nan)

    for a in range(len(swing_low_idx) - 2):
        i1, i2, i3 = swing_low_idx[a], swing_low_idx[a + 1], swing_low_idx[a + 2]
        if i3 - i1 < min_pattern_bars or i3 - i1 > max_pattern_bars:
            continue
        low1, low2, low3 = c[i1], c[i2], c[i3]
        lows = [low1, low2, low3]
        if (max(lows) - min(lows)) / min(lows) > bottom_tolerance_pct:
            continue
        peaks_between_1_2 = swing_high_idx[(swing_high_idx > i1) & (swing_high_idx < i2)]
        peaks_between_2_3 = swing_high_idx[(swing_high_idx > i2) & (swing_high_idx < i3)]
        if len(peaks_between_1_2) == 0 or len(peaks_between_2_3) == 0:
            continue
        peak1_val = c[peaks_between_1_2].max()
        peak2_val = c[peaks_between_2_3].max()
        confirmation_level = max(peak1_val, peak2_val)

        confirm_end = min(n, i3 + confirm_window + 1)
        for j in range(i3 + 1, confirm_end):
            if c[j] > confirmation_level:
                if not entry_cond[j]:
                    entry_cond[j] = True
                    confirm_level_at[j] = confirmation_level
                    bottom3_low_at[j] = low3
                break

    position = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = 0.0
    target_price = 0.0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            px = c[i]
            hit_stop = px < stop_price
            hit_target = px >= target_price
            hit_time = held >= max_hold_days
            if hit_stop or hit_target or hit_time:
                in_position = False
                position[i] = 0
                continue
            position[i] = 1
        else:
            if entry_cond[i]:
                in_position = True
                entry_idx = i
                stop_price = bottom3_low_at[i]
                measured_move = confirm_level_at[i] - bottom3_low_at[i]
                target_price = c[i] + reward_mult * measured_move
                position[i] = 1
            else:
                position[i] = 0

    return pd.Series(position, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
