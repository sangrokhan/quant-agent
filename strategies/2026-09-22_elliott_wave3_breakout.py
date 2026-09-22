"""Strategy: Elliott Wave 3 entry -- pullback + breakout confirmation, 1.618x
extension target.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-XXX):
Source: https://algobars.com/strategy-templates/elliott/wave-3-entry/
(accessed 2026-09-22, browser_exec after web_extract ddgs-backend refused
extraction). Wave 3 is "typically the longest and strongest impulse wave"
in Elliott Wave structure. Source's own numeric rule: identify a completed
"Wave 1" impulse (a swing-low-to-swing-high move), wait for a "Wave 2"
retracement of 50-78.6% of Wave 1, then enter LONG on a break above the
Wave 1 high (confirming the impulse resumes as Wave 3), targeting a 1.618x
Fibonacci extension of Wave 1's own length projected from the Wave 2 low.

Distinct from this repo's existing Fibonacci-retracement entry
(2026-09-03-022, near-miss rejected): that strategy enters DURING the
retracement itself (buy-the-dip, mean-reversion style) and exits on a new
swing high or a break below the swing low. This strategy instead waits for
the retracement to COMPLETE and only enters on the subsequent BREAKOUT
confirmation above the impulse high (trend-continuation style), with a
fixed Fibonacci-extension profit target (1.618x Wave 1's length) rather
than an open-ended "new swing high" exit -- a materially different
entry-trigger and exit-target mechanic despite sharing the same
50-78.6% retracement zone definition.

Signal logic (daily bars)
--------------------------
- Swing pivots detected via a rolling `pivot_window`-bar local extremum
  test (a bar is a swing low if it's the min low over the trailing+leading
  pivot_window bars; swing high analogously) -- same convention as this
  repo's existing AB=CD/Gartley/Bat/Crab/Butterfly/Cypher harmonic-pattern
  strategies.
- Wave 1 = the most recent completed swing-low(W1_start) to
  swing-high(W1_end) impulse move (W1_end must be the latest confirmed
  swing high after W1_start).
- Wave 2 = the subsequent retracement from W1_end; considered valid once
  price retraces into [retrace_min, retrace_max] (default 0.50-0.786) of
  the W1 range (W1_end - W1_start) without breaking below W1_start (a
  deeper retrace invalidates the count, per Elliott Wave's own rule that
  Wave 2 cannot retrace below the start of Wave 1).
- Entry (long): once a valid Wave 2 retracement has occurred, enter when a
  later close breaks back above W1_end (the Wave 1 high) within
  `breakout_expiry_days` of the retracement being confirmed.
- Exit: close reaches the 1.618x Fibonacci extension target
  (W1_end + `extension_mult` * (W1_end - W1_start)), OR close falls back
  below the Wave 2 retracement low (invalidation stop), OR a
  `max_hold_days` time-stop.
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


def _find_pivots(high: pd.Series, low: pd.Series, window: int):
    n = len(high)
    high_arr = high.to_numpy()
    low_arr = low.to_numpy()
    is_swing_high = np.zeros(n, dtype=bool)
    is_swing_low = np.zeros(n, dtype=bool)
    for i in range(window, n - window):
        seg_high = high_arr[i - window : i + window + 1]
        seg_low = low_arr[i - window : i + window + 1]
        if high_arr[i] == seg_high.max():
            is_swing_high[i] = True
        if low_arr[i] == seg_low.min():
            is_swing_low[i] = True
    return is_swing_high, is_swing_low


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 5,
    retrace_min: float = 0.50,
    retrace_max: float = 0.786,
    extension_mult: float = 1.618,
    breakout_expiry_days: int = 15,
    max_hold_days: int = 40,
) -> pd.Series:
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    is_swing_high, is_swing_low = _find_pivots(high, low, pivot_window)
    n = len(df)
    high_arr = high.to_numpy()
    low_arr = low.to_numpy()
    close_arr = close.to_numpy()

    pos_arr = [0] * n
    in_pos = False
    hold_days = 0
    entry_stop = None
    entry_target = None

    last_swing_low_idx = None
    last_swing_low_val = None

    # Wave-1 tracking: once we see swing_low then a later swing_high, that's W1.
    w1_start_val = None  # swing low value (start of Wave 1)
    w1_end_val = None    # swing high value (end of Wave 1 / Wave 1 high)
    w2_valid = False
    w2_low = None
    w2_confirmed_idx = None

    for i in range(n):
        # Update pivot tracking (lag-free at pivot_window bars, inherent to
        # the local-extremum test's own trailing+leading window).
        if is_swing_low[i]:
            last_swing_low_idx = i
            last_swing_low_val = low_arr[i]
            # A new swing low resets any in-progress wave count.
            w1_start_val = last_swing_low_val
            w1_end_val = None
            w2_valid = False
            w2_low = None
            w2_confirmed_idx = None
        if is_swing_high[i] and w1_start_val is not None and w1_end_val is None:
            # This becomes the Wave 1 high (end of the impulse).
            w1_end_val = high_arr[i]

        if in_pos:
            hold_days += 1
            hit_target = (entry_target is not None) and close_arr[i] >= entry_target
            hit_stop = (entry_stop is not None) and close_arr[i] < entry_stop
            if hit_target or hit_stop or hold_days >= max_hold_days:
                in_pos = False
                pos_arr[i] = 0
                hold_days = 0
            else:
                pos_arr[i] = 1
            continue

        # Track Wave 2 retracement validity once Wave 1 is established.
        if w1_start_val is not None and w1_end_val is not None and w1_end_val > w1_start_val:
            w1_range = w1_end_val - w1_start_val
            retrace_frac = (w1_end_val - low_arr[i]) / w1_range if w1_range > 0 else 0.0

            if low_arr[i] < w1_start_val:
                # Retrace exceeded 100% of Wave 1 -- invalidated count.
                w1_start_val = None
                w1_end_val = None
                w2_valid = False
                w2_low = None
                w2_confirmed_idx = None
            elif retrace_min <= retrace_frac <= retrace_max:
                if not w2_valid or (w2_low is not None and low_arr[i] < w2_low):
                    w2_low = low_arr[i] if w2_low is None else min(w2_low, low_arr[i])
                w2_valid = True
                w2_confirmed_idx = i

            # Check for breakout entry once Wave 2 has been confirmed.
            if (
                w2_valid
                and w2_confirmed_idx is not None
                and (i - w2_confirmed_idx) <= breakout_expiry_days
                and close_arr[i] > w1_end_val
            ):
                in_pos = True
                hold_days = 0
                entry_stop = w2_low
                entry_target = w1_end_val + extension_mult * w1_range
                pos_arr[i] = 1
                # Reset the wave count after entering (avoid re-triggering).
                w1_start_val = None
                w1_end_val = None
                w2_valid = False
                w2_low = None
                w2_confirmed_idx = None
                continue

        pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    pivot_window: int = 5,
    retrace_min: float = 0.50,
    retrace_max: float = 0.786,
    extension_mult: float = 1.618,
    breakout_expiry_days: int = 15,
    max_hold_days: int = 40,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        pivot_window=pivot_window,
        retrace_min=retrace_min,
        retrace_max=retrace_max,
        extension_mult=extension_mult,
        breakout_expiry_days=breakout_expiry_days,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
