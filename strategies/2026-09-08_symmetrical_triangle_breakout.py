"""Strategy: Symmetrical Triangle breakout, long-only.

Hypothesis (knowledge_base id=2026-09-08-102): Per
https://finwiz.io/chart-patterns/symmetrical-triangle, a symmetrical
triangle forms as converging trendlines (descending upper trendline of
lower highs, ascending lower trendline of higher lows), with volume
declining during the formation and expanding sharply on the breakout.
Source's stated mechanical rule: "Wait for a candle to close outside the
triangle on strong volume... Enter in the direction of the breakout,"
with stop "below the most recent swing low within the triangle" and
target "Breakout Price +/- Triangle Height (at widest point)". First
converging-trendline consolidation pattern tested in this repo (distinct
from the already-tested Bollinger/Bandwidth squeezes, which use fixed-
width volatility bands rather than an explicit pair of fitted trendlines
through swing highs/lows).

Signal logic
------------
- Identify confirmed swing highs and swing lows via a rolling pivot_window
  local-extremum test (same construction as the Double Bottom strategy in
  this repo, 2026-09-08_double_bottom_neckline_breakout.py).
- Over a trailing lookback_bars window, fit a simple linear regression
  through the swing highs (descending trendline) and through the swing
  lows (ascending trendline), each needing >= min_pivots points.
- A valid "triangle" state requires: upper-trendline slope < 0 (falling
  highs), lower-trendline slope > 0 (rising lows), and the triangle range
  (trendline vertical distance at the window's start) has contracted to
  <= contraction_ratio of that starting width by the current bar
  (compression, per source's "narrowing range" description).
- Entry (long): close breaks above the current upper-trendline value
  while in a valid triangle state, AND breakout-bar volume >=
  vol_expansion_mult x its own vol_lookback-day average volume (source:
  "Volume 50-100% above the recent average" -- vol_expansion_mult=1.5 is
  the low end of that band).
- Exit: close falls below the most recent confirmed swing low inside the
  triangle (source's stop rule), OR close reaches the measured-move
  target (breakout price + triangle height at its widest point within the
  lookback window), OR a max_hold_days time-stop backstop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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
    """Boolean series: True where `series` is a confirmed local extremum
    (mode='max' for swing highs, mode='min' for swing lows) over a
    +/- pivot_window bar window.
    """
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
    """OLS slope/intercept for ys = slope*xs + intercept."""
    if len(xs) < 2:
        return 0.0, float(ys[-1]) if len(ys) else 0.0
    A = np.vstack([xs, np.ones(len(xs))]).T
    slope, intercept = np.linalg.lstsq(A, ys, rcond=None)[0]
    return float(slope), float(intercept)


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 4,
    lookback_bars: int = 60,
    min_pivots: int = 2,
    contraction_ratio: float = 0.6,
    vol_expansion_mult: float = 1.5,
    vol_lookback: int = 20,
    target_mult: float = 1.0,
    max_hold_days: int = 25,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)
    n = len(df)

    is_swing_high = _swing_points(high, pivot_window, "max")
    is_swing_low = _swing_points(low, pivot_window, "min")
    avg_vol = volume.rolling(vol_lookback).mean()

    # Precompute numpy arrays once (avoid repeated .iloc[] pandas overhead
    # inside the O(n) main loop below).
    close_a = close.values.astype(float)
    high_a = high.values.astype(float)
    low_a = low.values.astype(float)
    vol_a = volume.values.astype(float)
    avg_vol_a = avg_vol.values.astype(float)
    swing_high_idx_all = np.flatnonzero(is_swing_high.values)
    swing_low_idx_all = np.flatnonzero(is_swing_low.values)

    position_a = np.zeros(n, dtype=int)

    in_position = False
    entry_idx = 0
    stop_price = None
    target_price = None

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

        if i < lookback_bars + pivot_window:
            position_a[i] = 0
            continue

        window_start = i - lookback_bars

        # np.searchsorted on the precomputed sorted pivot-index arrays --
        # O(log n) instead of an O(lookback_bars) Python list comprehension.
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

        # Triangle range contraction: width at window_start vs width now (at bar i).
        width_start = (slope_high * window_start + intercept_high) - (slope_low * window_start + intercept_low)
        width_now = (slope_high * i + intercept_high) - (slope_low * i + intercept_low)
        if width_start <= 0 or width_now <= 0 or (width_now / width_start) > contraction_ratio:
            position_a[i] = 0
            continue

        upper_line_now = slope_high * i + intercept_high
        c = close_a[i]
        v = vol_a[i]
        av = avg_vol_a[i]

        if c > upper_line_now and av and av > 0 and v >= vol_expansion_mult * av:
            if len(swing_low_idxs) == 0:
                position_a[i] = 0
                continue
            stop_price = float(low_a[swing_low_idxs[-1]])
            triangle_height = width_start  # widest point within the lookback window
            target_price = c + target_mult * triangle_height
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
