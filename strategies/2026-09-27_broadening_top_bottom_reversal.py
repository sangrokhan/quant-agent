"""Strategy: Bulkowski Broadening Top/Bottom "buy at 3rd touch" reversal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-124):
Per Thomas Bulkowski's ThePatternSite.com "Broadening Tops" page
(https://www.thepatternsite.com/bt.html, read via browser_exec this
iteration), a broadening formation is a "megaphone" pattern: an upper
trendline connecting swing highs that slopes UPWARD, and a lower trendline
connecting swing lows that slopes DOWNWARD (price range widening over
time), requiring at least 3 touches on each side. The source's own
disclosed "Intraformation trade" / "Buy at 3rd touch" tactic: "When price
touches the bottom trendline for the third time and begins rising, buy"
(explicitly flagged by the source as "a high risk entry"), with a mirrored
"Short at the top" tactic when price touches the upper trendline and turns
down.

This is a genuinely new pattern family for this repo (zero prior
"broadening"/"diamond"/"megaphone" hits in strategies_index.jsonl) --
distinct from all previously-tested classic chart patterns (double
top/bottom, triangles, wedges, flags, head-and-shoulders, cup-and-handle),
none of which use this specific widening-trendline / touch-count
construction.

Signal logic (long-only per SAFETY.md and this repo's convention)
-------------------------------------------------------------------
1. Detect local swing highs/lows over a rolling `pivot_window` (a bar is a
   pivot high/low if it's the max/min of a `+-pivot_window` bar
   neighborhood).
2. Over a trailing `lookback` window, collect the last 3+ pivot highs and
   last 3+ pivot lows. Fit a simple linear regression (index vs price) to
   each set to get the upper-trendline slope and lower-trendline slope.
3. "Broadening regime" is active when the upper-trendline slope is
   positive AND the lower-trendline slope is negative (megaphone shape)
   over the lookback window, with at least `min_touches` pivot lows
   registered (approximating the source's "at least five touches total"
   identification guideline, simplified to touch-count on the buy side
   since this is a long-only implementation).
4. Long entry: in an active broadening regime, price closes within
   `touch_tolerance` (fraction of price) of the projected lower-trendline
   value AND the most recent close-to-close return has turned positive
   (price "begins rising" off the touch, per the source's own trigger
   condition), AND this qualifies as at least the `min_touches`'th
   distinct lower-trendline touch within the lookback window.
5. Exit: close reaches/crosses the projected upper-trendline value (the
   source's mirror "short at the top" level, used here as a take-profit
   for the long-only version), OR the broadening regime breaks down
   (either slope condition fails), OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
Both accept every tunable parameter as a keyword argument per Step 5 of
RESEARCH_LOOP.md, since validation/grid_test.py calls
generate_returns_fn(price_df, **params) directly across a parameter grid.
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


def _find_pivots(close: pd.Series, pivot_window: int) -> tuple[pd.Series, pd.Series]:
    """Return boolean Series marking pivot-high and pivot-low bars.

    A bar is a pivot high/low if it is the strict max/min within a
    +-pivot_window neighborhood (simple, look-ahead-free once shifted by
    the caller -- pivots are only usable pivot_window bars after they
    occur, since confirming a pivot requires seeing the bars after it).
    """
    n = len(close)
    vals = close.values
    is_high = np.zeros(n, dtype=bool)
    is_low = np.zeros(n, dtype=bool)
    for i in range(pivot_window, n - pivot_window):
        window = vals[i - pivot_window : i + pivot_window + 1]
        if vals[i] == window.max() and (window == vals[i]).sum() == 1:
            is_high[i] = True
        if vals[i] == window.min() and (window == vals[i]).sum() == 1:
            is_low[i] = True
    return pd.Series(is_high, index=close.index), pd.Series(is_low, index=close.index)


def _trendline_projection(idxs: np.ndarray, vals: np.ndarray, target_idx: int) -> tuple[float, float]:
    """OLS fit of vals ~ idxs; returns (slope, projected value at target_idx)."""
    if len(idxs) < 2:
        return 0.0, float(vals[-1]) if len(vals) else np.nan
    slope, intercept = np.polyfit(idxs, vals, 1)
    return float(slope), float(slope * target_idx + intercept)


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 5,
    lookback: int = 60,
    min_touches: int = 3,
    touch_tolerance: float = 0.015,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    is_high, is_low = _find_pivots(close, pivot_window)
    # Pivots are only "known" pivot_window bars after they occur (need the
    # trailing bars to confirm the local extreme) -- shift confirmation
    # forward so there is no look-ahead.
    confirmed_high = is_high.shift(pivot_window).fillna(False).astype(bool)
    confirmed_low = is_low.shift(pivot_window).fillna(False).astype(bool)

    position = np.zeros(n, dtype=int)
    in_position = False
    entry_i = -1
    lower_touch_count = 0
    last_lower_val = None

    idx_arr = np.arange(n)
    close_arr = close.values

    for i in range(lookback, n):
        window_start = i - lookback
        highs_mask = confirmed_high.values[window_start:i]
        lows_mask = confirmed_low.values[window_start:i]
        high_idxs = idx_arr[window_start:i][highs_mask]
        high_vals = close_arr[window_start:i][highs_mask]
        low_idxs = idx_arr[window_start:i][lows_mask]
        low_vals = close_arr[window_start:i][lows_mask]

        if in_position:
            held = i - entry_i
            upper_slope, upper_proj = _trendline_projection(high_idxs, high_vals, i) if len(high_idxs) >= 2 else (0.0, np.inf)
            lower_slope, lower_proj = _trendline_projection(low_idxs, low_vals, i) if len(low_idxs) >= 2 else (0.0, -np.inf)
            regime_broken = not (upper_slope > 0 and lower_slope < 0)
            hit_target = close_arr[i] >= upper_proj
            time_out = held >= max_hold_days
            if hit_target or regime_broken or time_out:
                in_position = False
                position[i] = 0
                continue
            position[i] = 1
            continue

        # Not in position: check for a fresh 3rd-touch entry.
        if len(low_idxs) < min_touches or len(high_idxs) < 2:
            continue
        lower_slope, lower_proj = _trendline_projection(low_idxs, low_vals, i)
        upper_slope, _upper_proj = _trendline_projection(high_idxs, high_vals, i)
        if not (upper_slope > 0 and lower_slope < 0):
            continue  # not a broadening (megaphone) regime

        near_lower = abs(close_arr[i] - lower_proj) <= touch_tolerance * abs(lower_proj if lower_proj != 0 else close_arr[i])
        turning_up = close_arr[i] > close_arr[i - 1]
        touch_count = len(low_idxs)  # distinct confirmed pivot lows feeding the trendline this bar

        if near_lower and turning_up and touch_count >= min_touches:
            in_position = True
            entry_i = i
            position[i] = 1

    return pd.Series(position, index=close.index, name="position")


def generate_returns(
    price_df: pd.DataFrame,
    pivot_window: int = 5,
    lookback: int = 60,
    min_touches: int = 3,
    touch_tolerance: float = 0.015,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    pos = generate_signals(
        df,
        pivot_window=pivot_window,
        lookback=lookback,
        min_touches=min_touches,
        touch_tolerance=touch_tolerance,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    # Trade on next bar's return (avoid look-ahead: signal computed off
    # today's close, position taken effective for tomorrow's return).
    strat_ret = pos.shift(1).fillna(0) * daily_ret
    return strat_ret.rename("strategy_return")
