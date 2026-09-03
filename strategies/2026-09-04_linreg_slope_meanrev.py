"""Strategy: Linear Regression Slope mean-reversion (negative-slope entry, time-stop exit).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-058):
Per QuantifiedStrategies' Linear Regression Slope article: a rolling
N-day OLS slope of the close price is a trend-strength/direction
oscillator -- distinct calculation basis from every prior indicator in
this repo (computes an actual least-squares slope coefficient, not any
moving-average or price-range ratio). Source's own SPY backtest found the
NEGATIVE-slope mean-reversion variant (bet that a short-term downtrend
bounces) outperforms the positive-slope trend-following variant, best at
a fixed 9-day hold, though it still lagged buy-and-hold overall.

Rule: long entry at close when the rolling `slope_window`-day linear
regression slope of price is negative (below `slope_threshold`, default
0.0); exit unconditionally after `hold_days` trading days (fixed time
stop, per source's own backtested best variant).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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


def _rolling_slope(close: pd.Series, window: int) -> pd.Series:
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_demeaned = x - x_mean
    denom = (x_demeaned ** 2).sum()

    def slope_fn(y: np.ndarray) -> float:
        y_demeaned = y - y.mean()
        return float((x_demeaned * y_demeaned).sum() / denom)

    return close.rolling(window).apply(slope_fn, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    slope_window: int = 5,
    slope_threshold: float = 0.0,
    hold_days: int = 9,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    slope = _rolling_slope(close, slope_window)
    entry_signal = slope < slope_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_counter = 0
    for i in range(len(close)):
        if in_position:
            hold_counter += 1
            if hold_counter >= hold_days:
                in_position = False
                hold_counter = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_position = True
                hold_counter = 0
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
