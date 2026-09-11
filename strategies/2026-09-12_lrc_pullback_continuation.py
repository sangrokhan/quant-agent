"""Strategy: Linear Regression Channel (LRC) pullback continuation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-12-150):
Per https://trendsandbreakouts.com/linear-regression-channel ("Practical
Rules for Entries, Exits, Stops, and Filters"): "Trend filter: Only take
longs when the LRC slope is positive and price is above the regression
line... Entry for continuation: Enter on a pullback toward the regression
line that holds... Exit logic: ... in trends trail using the regression
line."

Operationalized here as a fully mechanical long-only rule:
- Fit a rolling linear-regression line (least squares) over the last
  `lrc_window` closes; slope estimated as (regline[t]-regline[t-slope_lag])
  / slope_lag.
- "Pullback that holds": within the last `pullback_window` bars price
  dipped to/below the regression line (close <= regline on at least one of
  those bars) and has now closed back above it.
- Entry (long): slope > 0 AND close > regline AND a qualifying pullback
  (as above) occurred within `pullback_window` bars AND today's close is
  the bar price reclaims the line.
- Exit: close crosses back below the regression line (trend-line trail
  broken, per source's own "trail using the regression line"), OR slope
  flips negative, OR a max_hold_days time-stop.

This is architecturally distinct from every prior regression-based entry
in this repo (Ehlers/DSMA/R-squared-gated crossover family) because it is
the first strategy to trade the LRC's own defined *pullback-to-the-line*
continuation setup rather than a slope-only trend filter or a channel-band
breakout/fade.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
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


def _rolling_linreg(close: pd.Series, window: int) -> pd.Series:
    """Rolling least-squares regression line value at the LAST bar of each
    window (i.e. the fitted value at t, using bars [t-window+1, t])."""
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    def _fit_last(vals: np.ndarray) -> float:
        y = vals
        y_mean = y.mean()
        slope = ((x - x_mean) * (y - y_mean)).sum() / x_var
        intercept = y_mean - slope * x_mean
        return intercept + slope * x[-1]

    return close.rolling(window).apply(_fit_last, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    lrc_window: int = 50,
    slope_lag: int = 5,
    pullback_window: int = 5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    regline = _rolling_linreg(close, lrc_window)
    slope = (regline - regline.shift(slope_lag)) / slope_lag

    above_line = close > regline
    below_or_at_line = close <= regline

    # "pullback that holds": touched/dipped to the line within the last
    # pullback_window bars (excluding today) and today reclaims it.
    recent_touch = below_or_at_line.shift(1).rolling(pullback_window).max().fillna(0).astype(bool)
    reclaim_today = above_line & (~below_or_at_line.shift(1).fillna(False))

    entry = (slope > 0) & above_line & recent_touch & reclaim_today
    exit_trend_break = (close < regline) | (slope <= 0)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
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
