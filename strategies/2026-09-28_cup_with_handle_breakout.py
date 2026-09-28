"""Strategy: Bulkowski Cup with Handle breakout (long-only continuation).

Hypothesis, sourced from https://thepatternsite.com/cup.html (Thomas
Bulkowski's "Encyclopedia of Chart Patterns" stats page; read via
browser_exec after web_search's DDGS backend returned no results for two
related pattern queries this iteration). Source's own disclosed
statistics and identification rules:

    "Cup with Handle: Important Bull Market Results: Overall performance
    rank (1 is best): 3 out of 39. Break even failure rate: 5%. Average
    rise: 54%. Throwback rate: 62%. Percentage meeting price target: 61%.
    ... U-shaped cup: The cup should be U-shaped, not V-shaped. Handle:
    The cup must have a handle on the right, 1 week minimum with no
    maximum, forming in the upper half of the cup. ... Buy when price
    closes above the right cup rim. Stop: the handle low is a good place
    to put a stop. ... Short handle: Stocks with handles shorter than the
    median 22 days show superior post breakout performance."

This repo already tested plain "Rounding Bottom" (2026-09-24-101/102,
accepted QQQ+SPY) -- a bowl shape with confirmation on close above the
LEFT lip. Cup with Handle is a genuinely distinct, source-disclosed
variant with rank #3 of 39 (vs Rounding Bottom's #7 of 39) and a
materially higher average rise (54% vs 48%): it requires the SAME bowl
(cup) shape PLUS an additional handle-consolidation phase after the right
cup rim is reached, with confirmation only on a breakout ABOVE the RIGHT
cup rim (not the left lip) -- and per the source's own "short handle"
trading tip, this implementation additionally requires the handle to be
shorter than a `handle_max_days` cutoff, since the source found
below-median-length handles show superior post-breakout performance.
First Cup-with-Handle entry in this repo (0 prior index hits for "cup
with handle" / "cup_and_handle").

Signal logic (numeric proxy for the source's qualitative pattern)
------------------------------------------------------------------
1. Cup (bowl) detection: identical bowl-window/center-tolerance logic to
   this repo's accepted Rounding Bottom strategy -- over a rolling
   `cup_window`-bar lookback, find the bar-index of the minimum close
   (the cup's lowest valley). Require that minimum to fall roughly in the
   MIDDLE of the window (within `center_tolerance`), proxying a smooth
   U-shaped turn rather than a sharp V-spike.
2. Right cup rim: the close at the END of the cup window (the most recent
   bar of the lookback), used as the breakout confirmation level --
   distinct from Rounding Bottom's left-lip confirmation.
3. Prior uptrend filter: close at the START of the cup window is above
   its own SMA(trend_lookback) (source: cup with handle rises into the
   pattern).
4. Handle phase: AFTER the cup completes (right rim reached), require
   price to consolidate in the upper half of the cup range (between the
   right rim and the rim minus `handle_depth_pct` * cup height) for at
   least `handle_min_days` and no more than `handle_max_days` bars before
   the breakout is allowed to fire -- proxying the source's "handle forms
   in the upper half of the cup, 1 week minimum" and the "short handle
   outperforms" trading tip.
5. Entry: first bar after the handle phase where close closes above the
   right cup rim (source's own disclosed buy rule).
6. Exit: source's own Measure Rule (height = right_rim - valley_price,
   target = right_rim + height * target_pct, source's own disclosed 61%
   "percentage meeting price target"), OR close falling back below the
   handle low (source's own disclosed stop placement), OR a
   max_hold_days time-stop, whichever comes first.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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
    cup_window: int = 60,
    center_tolerance: float = 0.30,
    trend_lookback: int = 50,
    handle_min_days: int = 5,
    handle_max_days: int = 22,
    handle_depth_pct: float = 0.5,
    target_pct: float = 0.61,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    close_arr = close.to_numpy()
    n = len(close_arr)

    sma_trend = close.rolling(trend_lookback).mean()
    sma_arr = sma_trend.to_numpy()

    # Step 1: find valid cup completions (bar index i = right cup rim bar)
    mid_tol = center_tolerance * cup_window
    cup_valid = np.zeros(n, dtype=bool)
    cup_right_rim = np.full(n, np.nan)
    cup_valley = np.full(n, np.nan)

    for i in range(cup_window, n):
        window = close_arr[i - cup_window: i]
        valley_offset = int(np.argmin(window))
        valley_price = window[valley_offset]
        mid = cup_window / 2.0
        if abs(valley_offset - mid) > mid_tol:
            continue
        left_bar = i - cup_window
        if np.isnan(sma_arr[left_bar]) or close_arr[left_bar] <= sma_arr[left_bar]:
            continue  # prior uptrend filter failed
        if valley_offset >= cup_window - 1:
            continue  # valley too close to the right edge, not a completed cup
        right_rim = close_arr[i]
        if right_rim <= valley_price:
            continue
        cup_valid[i] = True
        cup_right_rim[i] = right_rim
        cup_valley[i] = valley_price

    # Step 2: walk forward, track handle phase after each valid cup completion,
    # fire an entry once handle constraints are satisfied and price breaks
    # back above the right rim.
    position = np.zeros(n, dtype=int)
    in_pos = False
    entry_bar = -1
    entry_target = np.nan
    entry_stop = np.nan

    watching = False
    cup_bar = -1
    right_rim = np.nan
    valley_price = np.nan
    handle_low = np.inf
    handle_days = 0

    for t in range(n):
        if in_pos:
            position[t] = 1
            held = t - entry_bar
            failed = close_arr[t] < entry_stop
            hit_target = close_arr[t] >= entry_target
            if failed or hit_target or held >= max_hold_days:
                in_pos = False
            continue

        if cup_valid[t] and not watching:
            watching = True
            cup_bar = t
            right_rim = cup_right_rim[t]
            valley_price = cup_valley[t]
            handle_low = right_rim
            handle_days = 0
            continue

        if watching:
            handle_days += 1
            cup_height = right_rim - valley_price
            upper_half_floor = right_rim - handle_depth_pct * cup_height
            if close_arr[t] < upper_half_floor:
                # handle dropped too deep, cup invalidated
                watching = False
                continue
            handle_low = min(handle_low, close_arr[t])
            if handle_days > handle_max_days:
                watching = False
                continue
            if handle_days >= handle_min_days and close_arr[t] > right_rim:
                height = right_rim - valley_price
                target_price = right_rim + height * target_pct if height > 0 else np.inf
                in_pos = True
                entry_bar = t
                entry_target = target_price
                entry_stop = handle_low
                position[t] = 1
                watching = False

    return pd.Series(position, index=close.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
