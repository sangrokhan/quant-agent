"""Strategy: Single-state Kalman-filter trend line crossover with a regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-052):
Follow-up to already-rejected 2026-09-05-056 (dual fast/slow Kalman filter
percentile-breakout construction). Per theforexgeek.com's Kalman Filter
Trading Strategy "Trend Estimation" implementation: a SINGLE 1D Kalman
filter (constant-velocity local-level model) produces a smooth, low-lag
adaptive trend-line estimate of price. Entry signal: price crosses above the
Kalman trend-line estimate (bullish), exit when it crosses back below. This
is a simpler, more direct construction than -056's dual-filter percentile
approach -- testing whether the earlier rejection was specific to the
dual-filter/percentile-rescaling complexity rather than Kalman filtering
itself. Adds a basic trend-direction filter (Kalman-estimated slope
positive) to avoid whipsaws in flat/declining regimes, per the source's own
advice to pair the trend estimate with directional confirmation.

Signal logic
------------
- 1D Kalman filter (local level + trend state) over close price:
  state = [level, slope]; process noise q, measurement noise r (ratio
  q/r controls responsiveness -- kalman_q parameter, r fixed at 1.0).
- Kalman trend-line estimate = filtered level at each bar.
- Entry (long): close crosses above the Kalman level estimate AND the
  Kalman-estimated slope (level[t] - level[t-1]) is positive.
- Exit: close crosses back below the Kalman level estimate, OR after
  max_hold_days trading days.
- Flat (no position) whenever not in an active long.

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


def _kalman_trend(close: pd.Series, kalman_q: float) -> pd.Series:
    """Simple constant-velocity 1D Kalman filter (level + slope state) over
    close price. Returns the filtered level estimate series."""
    vals = close.values
    n = len(vals)
    level = np.full(n, np.nan)

    if n == 0:
        return pd.Series(level, index=close.index)

    # State: [level, slope]. Process noise scales with kalman_q; measurement
    # noise fixed at 1.0 (kalman_q controls the responsiveness ratio).
    x = np.array([vals[0], 0.0])
    P = np.eye(2) * 1.0
    F = np.array([[1.0, 1.0], [0.0, 1.0]])
    H = np.array([[1.0, 0.0]])
    Q = np.eye(2) * kalman_q
    R = np.array([[1.0]])

    level[0] = x[0]
    for i in range(1, n):
        # Predict
        x = F @ x
        P = F @ P @ F.T + Q
        # Update
        z = vals[i]
        if np.isnan(z):
            level[i] = x[0]
            continue
        y = z - (H @ x)[0]
        S = (H @ P @ H.T)[0, 0] + R[0, 0]
        K = (P @ H.T) / S
        x = x + (K.flatten() * y)
        P = (np.eye(2) - K @ H) @ P
        level[i] = x[0]

    return pd.Series(level, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    kalman_q: float = 0.01,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    kalman_level = _kalman_trend(close, kalman_q)
    slope_up = kalman_level.diff() > 0
    cross_above = (close > kalman_level) & (close.shift(1) <= kalman_level.shift(1))
    cross_below = close < kalman_level

    entry = cross_above & slope_up.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(cross_below.iloc[i]) or held >= max_hold_days:
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
