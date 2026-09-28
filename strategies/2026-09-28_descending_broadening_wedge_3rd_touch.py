"""Strategy: Bulkowski Descending Broadening Wedge "buy at 3rd touch".

Hypothesis (source: https://thepatternsite.com/dbw.html, Thomas Bulkowski,
read 2026-09-28 via browser_exec):

The Descending Broadening Wedge is a "megaphone tilted down": BOTH
trendlines slope downward (upper trendline through swing highs AND lower
trendline through swing lows both decline), with at least 5 total
trendline touches (>=3 on one side, >=2 on the other). This is
mechanically DISTINCT from this repo's already-tested Broadening Top
(2026-09-24-107, 2026-09-27-124), where the upper trendline slopes UP
and the lower slopes DOWN (a true symmetric megaphone) -- the Descending
Broadening Wedge instead has both boundaries declining, just at
different rates, so the range still widens but the whole formation
drifts down. Source's own disclosed trading tactic ("Buy at 3rd touch"):
"When price touches the bottom trendline for the third time... and
begins rising, buy. Price may breakout on the following trip across the
chart pattern." Source's own stats: breakout direction is upward 72% of
the time; average rise on upward breakout 39%; break-even failure rate
18% for upward breakouts.

Mechanical proxy (daily-bar, long-only): reuses swing-pivot detection.
  1. Detect swing highs/lows via a centered rolling-window fractal test.
  2. Fit a linear trendline (least squares) through the most recent
     `n_touches_required` swing lows within a trailing
     `pattern_lookback`-bar window, and separately through the most
     recent swing highs in the same window.
  3. Require BOTH trendlines to have a NEGATIVE slope (the defining
     "both boundaries decline" property) and the lower trendline's slope
     to be less steep (closer to flat/higher) than the upper trendline's
     -- i.e. the range widens as it descends (megaphone shape tilted
     down), checked via slope_lower > slope_upper (both negative, lower
     less negative).
  4. "3rd touch" entry: count the times price has touched (come within
     `touch_tolerance` of) the projected lower trendline level. On the
     THIRD such touch, if price begins rising on the next bar (close >
     that bar's close), enter long.
  5. Exit: close crosses below the touch-point stop level, close reaches
     the projected upper trendline level (measure-rule-style target), or
     a max_hold_days time-stop.

Interface contract (see validation/validators.py and validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _find_pivots(series: pd.Series, window: int) -> pd.Series:
    n = len(series)
    pivots = pd.Series(0, index=series.index, dtype=int)
    half = window // 2
    vals = series.values
    for i in range(half, n - half):
        window_vals = vals[i - half: i + half + 1]
        if vals[i] == window_vals.max() and (window_vals == vals[i]).sum() == 1:
            pivots.iloc[i] = 1
        elif vals[i] == window_vals.min() and (window_vals == vals[i]).sum() == 1:
            pivots.iloc[i] = -1
    return pivots


def _fit_trendline(xs, ys):
    if len(xs) < 2:
        return None
    xs = np.array(xs, dtype=float)
    ys = np.array(ys, dtype=float)
    slope, intercept = np.polyfit(xs, ys, 1)
    return slope, intercept


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 9,
    pattern_lookback: int = 80,
    n_touches_required: int = 3,
    touch_tolerance: float = 0.015,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series for descending broadening
    wedge 'buy at 3rd touch' entries."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    high_pivots = _find_pivots(high, pivot_window)
    low_pivots = _find_pivots(low, pivot_window)

    low_idx_all = [i for i in range(len(df)) if low_pivots.iloc[i] == -1]
    high_idx_all = [i for i in range(len(df)) if high_pivots.iloc[i] == 1]

    c_arr = close.to_numpy()
    low_arr = low.to_numpy()
    high_arr = high.to_numpy()
    n = len(c_arr)

    position = pd.Series(0.0, index=df.index)
    in_pos = False
    hold_count = 0
    stop_price = 0.0
    target_price = 0.0

    touch_count = 0
    last_touch_idx = -10
    active_lower_slope = None
    active_lower_intercept = None
    active_upper_level = None

    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = (
                c_arr[i] < stop_price
                or c_arr[i] >= target_price
                or hold_count >= max_hold_days
            )
            if exit_now:
                in_pos = False
                hold_count = 0
                touch_count = 0
            else:
                position.iloc[i] = 1.0
                continue

        if i < pattern_lookback:
            continue

        window_start = i - pattern_lookback
        recent_lows = [(idx, low_arr[idx]) for idx in low_idx_all if window_start <= idx <= i]
        recent_highs = [(idx, high_arr[idx]) for idx in high_idx_all if window_start <= idx <= i]

        if len(recent_lows) < 2 or len(recent_highs) < 2:
            continue

        low_fit = _fit_trendline([p[0] for p in recent_lows], [p[1] for p in recent_lows])
        high_fit = _fit_trendline([p[0] for p in recent_highs], [p[1] for p in recent_highs])
        if low_fit is None or high_fit is None:
            continue
        slope_lower, intercept_lower = low_fit
        slope_upper, intercept_upper = high_fit

        # Descending Broadening Wedge: both slopes negative, lower less
        # steep than upper (range widens as it descends).
        if not (slope_lower < 0 and slope_upper < 0 and slope_lower > slope_upper):
            continue

        projected_lower = slope_lower * i + intercept_lower
        projected_upper = slope_upper * i + intercept_upper
        if projected_upper <= projected_lower:
            continue

        # Touch detection: is today's low within tolerance of the
        # projected lower trendline?
        if abs(low_arr[i] - projected_lower) <= touch_tolerance * projected_lower and i - last_touch_idx > 2:
            touch_count += 1
            last_touch_idx = i
            active_lower_slope = slope_lower
            active_lower_intercept = intercept_lower
            active_upper_level = projected_upper

        if (
            not in_pos
            and touch_count >= n_touches_required
            and active_lower_slope is not None
            and i > last_touch_idx
            and c_arr[i] > c_arr[i - 1]
        ):
            in_pos = True
            hold_count = 0
            stop_price = low_arr[last_touch_idx]
            target_price = active_upper_level
            position.iloc[i] = 1.0
            touch_count = 0

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
