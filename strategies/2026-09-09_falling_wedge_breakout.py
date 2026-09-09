"""Strategy: Falling Wedge breakout (converging downward trendlines, bullish reversal).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-097):
Per Dukascopy Bank SA's Falling Wedge Pattern guide (Google search result,
query "rising wedge falling wedge chart pattern trading strategy exact
entry exit rules"): a falling wedge is two downward-sloping, converging
trendlines connecting a sequence of lower highs and lower lows, with the
highs falling faster than the lows (narrowing range) -- signaling waning
downward momentum. Source's exact trading rule: wait for a breakout above
the UPPER trendline (the descending-highs line) to enter long; place the
stop below the LOWER trendline; target the wedge's height projected up
from the breakout point.

Approximated here for daily-bar systematic backtesting: fit simple linear
regressions to the rolling-window highs and lows separately. A "falling
wedge" is confirmed when both slopes are negative (both lines
descending) AND the high-line's slope is more negative than the low-line's
slope (highs falling faster => converging/narrowing range) AND the
wedge's width (upper trendline value minus lower trendline value at the
window's last bar) has shrunk versus the window's start (confirms
narrowing, not just two arbitrary descending lines). Entry: close breaks
above the projected upper trendline value for the current bar. Exit: a
profit target at breakout_price + wedge_height (source's stated target
method), a stop-loss at the lower trendline value at breakout, or a
max_hold_days time-stop backstop.

First Wedge-pattern (converging trendline) strategy in this repo (0 prior
hits on "Wedge Pattern"/"Rising Wedge"/"Falling Wedge") -- distinct from
Darvas Box (event-triggered frozen box, no slope), TTM Squeeze/Bollinger
Bandwidth (volatility-band-width narrowing, not two independently-sloped
price trendlines), and Triangle patterns (not yet tested either but
structurally symmetric/ascending/descending rather than both-lines-
descending).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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


def _rolling_slope_and_level(series: pd.Series, window: int):
    """Return (slope, level_at_last_point) arrays via rolling OLS fit."""
    n = len(series)
    slopes = np.full(n, np.nan)
    levels = np.full(n, np.nan)
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()
    vals = series.values
    for i in range(window - 1, n):
        y = vals[i - window + 1 : i + 1]
        if np.isnan(y).any():
            continue
        y_mean = y.mean()
        slope = ((x - x_mean) * (y - y_mean)).sum() / x_var
        intercept = y_mean - slope * x_mean
        level = intercept + slope * (window - 1)  # value at last point in window
        slopes[i] = slope
        levels[i] = level
    return slopes, levels


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 20,
    narrow_ratio: float = 0.7,
    atr_window: int = 14,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    n = len(close)

    high_slope, high_level = _rolling_slope_and_level(high, window)
    low_slope, low_level = _rolling_slope_and_level(low, window)

    # Width at window start (proxy via high[i-window+1]-low[i-window+1]) vs width now.
    width_now = high_level - low_level
    start_high = high.shift(window - 1)
    start_low = low.shift(window - 1)
    width_start = (start_high - start_low).values

    is_falling_wedge = np.zeros(n, dtype=bool)
    for i in range(n):
        if np.isnan(high_slope[i]) or np.isnan(low_slope[i]) or np.isnan(width_start[i]):
            continue
        if high_slope[i] < 0 and low_slope[i] < 0 and high_slope[i] < low_slope[i]:
            if width_start[i] > 0 and width_now[i] < narrow_ratio * width_start[i]:
                is_falling_wedge[i] = True

    upper_trendline = pd.Series(high_level, index=close.index)
    lower_trendline = pd.Series(low_level, index=close.index)
    wedge_flag = pd.Series(is_falling_wedge, index=close.index)

    breakout = wedge_flag.shift(1).fillna(False) & (close > upper_trendline)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    target_price = None
    stop_price = None

    for i in range(n):
        if in_position:
            held = i - entry_idx
            hit_target = target_price is not None and close.iloc[i] >= target_price
            hit_stop = stop_price is not None and close.iloc[i] <= stop_price
            if hit_target or hit_stop or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                target_price = None
                stop_price = None
                continue
            position.iloc[i] = 1
        else:
            if bool(breakout.iloc[i]):
                wedge_height = upper_trendline.iloc[i] - lower_trendline.iloc[i]
                if wedge_height == wedge_height and wedge_height > 0:
                    in_position = True
                    entry_idx = i
                    target_price = close.iloc[i] + wedge_height
                    stop_price = lower_trendline.iloc[i]
                    position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
