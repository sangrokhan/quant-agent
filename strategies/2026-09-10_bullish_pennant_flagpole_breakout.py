"""Strategy: Bullish Pennant continuation breakout, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-004):
Per Alchemy Markets' "14 Continuation Patterns Traders Use to Ride Strong
Trends" (https://alchemymarkets.com/education/continuation-patterns/,
citing Thomas Bulkowski's chart-pattern research): "A bullish pennant
appears after a strong upward move that pushes price into a new high. At
the top of this impulse, price consolidates into a small symmetrical
triangle, where lower highs and higher lows form... Once the pennant
breaks, price typically continues in the direction of the prior impulse.
For a pennant, the MMT [measured move target] equals the height of the
'flagpole' -- the initial bullish impulse's height." Stop loss is placed
below the pennant's low.

This is mechanically DISTINCT from the already-tested Symmetrical
Triangle breakout (2026-09-08-102, rejected): that strategy detects a
converging-trendline consolidation ANYWHERE (no requirement that it
follows a sharp prior impulse to a fresh high) and targets the triangle's
OWN height. A Pennant is a symmetrical-triangle consolidation with two
extra, source-specified conditions this strategy adds: (1) it must be
preceded by a genuine "flagpole" -- a sharp, fast prior price advance
into a new N-day high -- and (2) its measured-move target is the
FLAGPOLE's height (the impulse leg), not the triangle's own (much
smaller) height, which per the source produces a materially larger
target than the plain symmetrical-triangle construction.

Signal logic
------------
- Flagpole detection: over the trailing `flagpole_window` bars, price
  must have advanced by at least `flagpole_min_pct` (a "strong, near-
  vertical" impulse per the source) AND the current bar's close must be
  at/near a fresh `flagpole_window`-bar high (within `new_high_tolerance`
  of the rolling max) -- this captures "pushes price into a new high."
- Following that impulse, detect a converging-trendline consolidation
  (identical swing-pivot + OLS-trendline-fit + contraction-ratio
  machinery as the existing Symmetrical Triangle strategy in this repo,
  for a fair apples-to-apples comparison of the entry-gate difference)
  over the subsequent `lookback_bars` window.
- Entry (long): close breaks above the current upper (converging) trend-
  line while a valid pennant (flagpole + triangle) state holds.
- Exit: close falls below the pennant's own low (stop, per source), OR
  close reaches the measured-move target = breakout price + flagpole
  height (high of the flagpole window minus its starting low), OR a
  `max_hold_days` time-stop backstop.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
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


def _swing_points(series: pd.Series, pivot_window: int, mode: str) -> pd.Series:
    n = len(series)
    is_pivot = pd.Series(False, index=series.index)
    vals = series.values
    for i in range(pivot_window, n - pivot_window):
        window = vals[i - pivot_window: i + pivot_window + 1]
        target = window.max() if mode == "max" else window.min()
        if vals[i] == target:
            is_pivot.iloc[i] = True
    return is_pivot


def _fit_line(xs: np.ndarray, ys: np.ndarray) -> tuple:
    if len(xs) < 2:
        return 0.0, float(ys[-1]) if len(ys) else 0.0
    A = np.vstack([xs, np.ones(len(xs))]).T
    slope, intercept = np.linalg.lstsq(A, ys, rcond=None)[0]
    return float(slope), float(intercept)


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 3,
    lookback_bars: int = 25,
    min_pivots: int = 2,
    contraction_ratio: float = 0.6,
    flagpole_window: int = 15,
    flagpole_min_pct: float = 0.08,
    new_high_tolerance: float = 0.02,
    max_hold_days: int = 25,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    n = len(df)

    is_swing_high = _swing_points(high, pivot_window, "max")
    is_swing_low = _swing_points(low, pivot_window, "min")

    close_a = close.values.astype(float)
    high_a = high.values.astype(float)
    low_a = low.values.astype(float)
    swing_high_idx_all = np.flatnonzero(is_swing_high.values)
    swing_low_idx_all = np.flatnonzero(is_swing_low.values)

    position_a = np.zeros(n, dtype=int)

    in_position = False
    entry_idx = 0
    stop_price = None
    target_price = None

    min_start = max(lookback_bars, flagpole_window) + pivot_window

    for i in range(n):
        if in_position:
            held = i - entry_idx
            c = close_a[i]
            if (c <= stop_price) or (c >= target_price) or (held >= max_hold_days):
                in_position = False
                position_a[i] = 0
                continue
            position_a[i] = 1
            continue

        if i < min_start:
            position_a[i] = 0
            continue

        # --- Flagpole check: sharp impulse into a fresh high over the
        # trailing flagpole_window bars, evaluated just before the
        # triangle consolidation window. ---
        fp_start = i - lookback_bars - flagpole_window
        fp_end = i - lookback_bars
        if fp_start < 0 or fp_end <= fp_start:
            position_a[i] = 0
            continue
        fp_low = low_a[fp_start:fp_end].min()
        fp_high = high_a[fp_start:fp_end].max()
        if fp_low <= 0:
            position_a[i] = 0
            continue
        flagpole_pct = (fp_high - fp_low) / fp_low
        rolling_high_at_fp_end = high_a[max(0, fp_end - flagpole_window):fp_end].max() if fp_end > 0 else fp_high
        near_fresh_high = fp_high >= rolling_high_at_fp_end * (1.0 - new_high_tolerance)

        if flagpole_pct < flagpole_min_pct or not near_fresh_high:
            position_a[i] = 0
            continue

        flagpole_height = fp_high - fp_low

        # --- Triangle consolidation check over lookback_bars leading up
        # to bar i (same construction as this repo's Symmetrical Triangle
        # strategy). ---
        window_start = i - lookback_bars

        lo = np.searchsorted(swing_high_idx_all, window_start, side="left")
        hi = np.searchsorted(swing_high_idx_all, i, side="right")
        swing_high_idxs = swing_high_idx_all[lo:hi]

        lo2 = np.searchsorted(swing_low_idx_all, window_start, side="left")
        hi2 = np.searchsorted(swing_low_idx_all, i, side="right")
        swing_low_idxs = swing_low_idx_all[lo2:hi2]

        if len(swing_high_idxs) < min_pivots or len(swing_low_idxs) < min_pivots:
            position_a[i] = 0
            continue

        xs_high = swing_high_idxs.astype(float)
        ys_high = high_a[swing_high_idxs]
        xs_low = swing_low_idxs.astype(float)
        ys_low = low_a[swing_low_idxs]

        slope_high, intercept_high = _fit_line(xs_high, ys_high)
        slope_low, intercept_low = _fit_line(xs_low, ys_low)

        if not (slope_high < 0 and slope_low > 0):
            position_a[i] = 0
            continue

        width_start = (slope_high * window_start + intercept_high) - (slope_low * window_start + intercept_low)
        width_now = (slope_high * i + intercept_high) - (slope_low * i + intercept_low)
        if width_start <= 0 or width_now <= 0 or (width_now / width_start) > contraction_ratio:
            position_a[i] = 0
            continue

        upper_line_now = slope_high * i + intercept_high
        c = close_a[i]

        if c > upper_line_now:
            if len(swing_low_idxs) == 0:
                position_a[i] = 0
                continue
            pennant_low = float(low_a[window_start:i + 1].min())
            stop_price = pennant_low
            target_price = c + flagpole_height
            if stop_price >= c or target_price <= c:
                position_a[i] = 0
                continue
            in_position = True
            entry_idx = i
            position_a[i] = 1
        else:
            position_a[i] = 0

    return pd.Series(position_a, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
