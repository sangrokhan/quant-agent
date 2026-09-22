"""Strategy: Elliott ABC Correction entry (Wave C completion long).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-XXX):
Source: https://algobars.com/strategy-templates/elliott/elliott-abc-correction/
(accessed 2026-09-22, browser_exec after web_extract ddgs-backend refused
extraction). After a strong bullish impulse move completes, price enters a
corrective ABC pullback: Wave A (initial pullback from the impulse peak),
Wave B (counter-rally, typically 0.382-0.618 retrace of A), Wave C (final
leg down, extends 0.618-1.272 of A). Long entry at Wave C's completion with
a bullish reversal candle, targeting a new high beyond the pre-correction
impulse peak. Source's explicit invalidation rules: Wave C extending beyond
1.618x of Wave A invalidates the count (likely a new downtrend, not a
correction); Wave B retracing more than 100% of Wave A also invalidates.

First Elliott ABC-correction strategy in this repo (0 prior KB hits for
"ABC Correction"/"Wave A"/"Wave B"/"Wave C" in the Elliott-Wave sense --
distinct from this cron trigger's own Wave 3 breakout entry 2026-09-22-095,
which trades the IMPULSE continuation via a breakout-above-Wave-1-high
mechanic, not a corrective-pullback-completion mean-reversion mechanic).

Signal logic (daily bars)
--------------------------
- Swing pivots via the same rolling `pivot_window`-bar local-extremum test
  used by this repo's other harmonic/Elliott-family strategies.
- Impulse peak = the most recent confirmed swing high (P).
- Wave A = the pullback from P to the next swing low (A_low).
- Wave B = the counter-rally from A_low to the next swing high (B_high);
  valid if B_high does NOT exceed P (source: B retracing >100% of A --
  i.e. price making a new high above P -- invalidates the ABC count as a
  correction, since it would mean the "correction" already resumed the
  uptrend rather than completing a genuine ABC).
- Wave C = the subsequent decline from B_high; entry evaluated once C's
  low falls into the source's stated completion zone
  [c_ext_min, c_ext_max] x (P - A_low) below B_high, i.e.
  C_extension = (B_high - low) / (P - A_low) in [0.618, 1.272] by default.
  If C_extension exceeds `c_invalidate_mult` (1.618), the count is
  invalidated (source's explicit rule).
- Entry (long): on the bar where C's extension first enters the valid
  completion zone AND that bar is a bullish reversal candle
  (close > open).
- Exit: close reaches a new high beyond P (source's stated minimum
  target), OR close falls below the Wave C low (invalidation stop), OR a
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
    c_ext_min: float = 0.618,
    c_ext_max: float = 1.272,
    c_invalidate_mult: float = 1.618,
    max_hold_days: int = 40,
) -> pd.Series:
    df = _prep(price_df)
    high, low, close, open_ = df["high"], df["low"], df["close"], df["open"]

    is_swing_high, is_swing_low = _find_pivots(high, low, pivot_window)
    n = len(df)
    high_arr = high.to_numpy()
    low_arr = low.to_numpy()
    close_arr = close.to_numpy()
    open_arr = open_.to_numpy()

    pos_arr = [0] * n
    in_pos = False
    hold_days = 0
    entry_stop = None
    entry_target = None

    # State machine: track P (impulse peak) -> A_low -> B_high -> await C.
    state = "await_peak"  # await_peak -> await_a_low -> await_b_high -> await_c
    P = None
    A_low = None
    B_high = None

    for i in range(n):
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

        # Update state machine on pivot events.
        if is_swing_high[i]:
            if state == "await_peak":
                P = high_arr[i]
                state = "await_a_low"
            elif state == "await_b_high":
                B_high = high_arr[i]
                if P is not None and B_high > P:
                    # B retraced beyond P -- invalidate, this is a new peak.
                    P = B_high
                    A_low = None
                    B_high = None
                    state = "await_a_low"
                else:
                    state = "await_c"
            elif state in ("await_a_low", "await_c"):
                # A fresh higher peak resets the count.
                if P is None or high_arr[i] > P:
                    P = high_arr[i]
                    A_low = None
                    B_high = None
                    state = "await_a_low"

        if is_swing_low[i]:
            if state == "await_a_low":
                A_low = low_arr[i]
                state = "await_b_high"

        # While awaiting C completion, check each bar for the completion zone.
        if state == "await_c" and P is not None and A_low is not None and B_high is not None:
            wave_a_range = P - A_low
            if wave_a_range > 0:
                c_extension = (B_high - low_arr[i]) / wave_a_range

                if c_extension > c_invalidate_mult:
                    # Invalidated -- likely a new downtrend, reset.
                    P = None
                    A_low = None
                    B_high = None
                    state = "await_peak"
                elif c_ext_min <= c_extension <= c_ext_max and close_arr[i] > open_arr[i]:
                    in_pos = True
                    hold_days = 0
                    entry_stop = low_arr[i]
                    entry_target = P
                    pos_arr[i] = 1
                    # Reset the wave count after entering.
                    P = None
                    A_low = None
                    B_high = None
                    state = "await_peak"
                    continue

        pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    pivot_window: int = 5,
    c_ext_min: float = 0.618,
    c_ext_max: float = 1.272,
    c_invalidate_mult: float = 1.618,
    max_hold_days: int = 40,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        pivot_window=pivot_window,
        c_ext_min=c_ext_min,
        c_ext_max=c_ext_max,
        c_invalidate_mult=c_invalidate_mult,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
