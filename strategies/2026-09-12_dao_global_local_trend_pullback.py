"""Strategy: Dual-Scale Trend Filter Momentum (global trend + local
mean-reversion pullback), per Dao's L1-filter momentum framework.

Hypothesis (see knowledge_base id 2026-09-12-176):
Per Tung-Lam Dao's "Momentum Strategies with L1 Filter" (Journal of
Investment Strategies 2014, arXiv:1403.4069): "Financial time series are
usually characterized by a long-term trend (called the global trend) and
some short-term trends (which are named local trends). A combination of
these two time scales can form a simple model describing the process of a
global trend process with some mean-reverting properties." The paper's own
L1 (piecewise-linear trend-filtering / total-variation) decomposition
requires a convex solver (not available in this repo's environment: no
cvxpy). This strategy implements the paper's own stated CONCEPTUAL
mechanism -- combining a long-horizon "global trend" direction with a
short-horizon "local trend" state to capture mean-reverting pullbacks
within an established trend -- using OLS regression-slope trend
estimation (already used elsewhere in this repo for trendline
constructions) as a directly implementable proxy for the L1-filtered
piecewise-linear trend segments, rather than reimplementing the paper's
specific convex-optimization solver from scratch.

Signal logic
------------
- Global trend: sign of the OLS-fit slope of close over a long
  `global_window`-bar lookback (the long-term trend direction).
- Local trend: sign of the OLS-fit slope of close over a short
  `local_window`-bar lookback (the recent, potentially mean-reverting
  short-term move).
- Per the paper's own framing (global trend WITH local mean-reverting
  pullbacks): long entry when global trend is UP (global slope > 0) AND
  the local trend has just turned from negative back to positive (a
  pullback-within-an-uptrend resolving back upward) -- i.e. buy the dip
  within the established trend, rather than chasing continuous momentum.
- Exit: local trend turns negative again, the global trend itself flips
  down, or a `max_hold_days` time-stop.

First Dao L1-filter-framework (global-trend + local-pullback) strategy in
this repo -- distinct from every other dual-timeframe trend/momentum
combination already tested (multi-horizon TSMOM vote, Triple Screen,
multi-timeframe RSI alignment) via its specific "buy the local-trend
pullback WITHIN an established global uptrend" mechanic derived directly
from the source's own stated global/local trend decomposition rationale.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
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


def _rolling_ols_slope(series: pd.Series, window: int) -> pd.Series:
    """Rolling OLS slope of `series` against a simple 0..window-1 x-axis,
    normalized by the series' own rolling mean to make the slope
    scale-invariant (comparable across different price levels/assets)."""
    x = np.arange(window)
    x_mean = x.mean()
    x_demeaned = x - x_mean
    denom = (x_demeaned ** 2).sum()

    values = series.to_numpy()
    n = len(values)
    slopes = np.full(n, np.nan)

    for i in range(window - 1, n):
        window_vals = values[i - window + 1 : i + 1]
        y_mean = window_vals.mean()
        if y_mean == 0:
            continue
        y_demeaned = window_vals - y_mean
        slope = (x_demeaned * y_demeaned).sum() / denom
        slopes[i] = slope / abs(y_mean)

    return pd.Series(slopes, index=series.index)


def generate_signals(
    price_df: pd.DataFrame,
    global_window: int = 100,
    local_window: int = 15,
    max_hold_days: int = 25,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    global_slope = _rolling_ols_slope(close, global_window)
    local_slope = _rolling_ols_slope(close, local_window)

    global_up = (global_slope > 0).fillna(False)
    local_up = (local_slope > 0).fillna(False)
    local_turned_up = (local_up & ~local_up.shift(1).fillna(False)).fillna(False)

    entry = (global_up & local_turned_up).fillna(False)
    exit_signal = (~local_up | ~global_up).fillna(True)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    global_window: int = 100,
    local_window: int = 15,
    max_hold_days: int = 25,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs here)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        global_window=global_window,
        local_window=local_window,
        max_hold_days=max_hold_days,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    return strat_returns
