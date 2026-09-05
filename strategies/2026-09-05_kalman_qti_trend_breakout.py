"""Strategy: Kalman-filter trend-percentile (QTI) breakout ("Fast trend
following" adapted from intraday futures to daily equity/crypto bars).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-056):
Per Quantitativo's "Fast trend following" article (quantitativo.com/p/fast-
trend-following), run two 1D Kalman filters over price with different
measurement-noise assumptions: a "fast" filter (low R, trusts observations,
tracks price closely) and a "slow" filter (high R, trusts its own
constant-velocity model, stays smooth). The pct difference between the fast
and slow filter estimates is itself rescaled into a rolling PERCENTILE RANK
("QTI" -- Quantitativo Trend Indicator) in [-100, +100]: +100 = fast filter
maximally above the slow filter (price accelerating away from trend, i.e.
strongly trending up), -100 = maximally below, 0 = right on trend. Entry:
QTI crosses above `entry_level` (fast filter just started pulling away from
trend -- an early, low-lag trend-start signal per the source's own
methodology). Exit: QTI reaches a `target_level` (trend matured/profit
target) OR falls back below `entry_level` (trend failed/stop), or a
`max_hold_days` time-stop (the source's original design has no such time
cap since it trades 1-minute bars intraday; added here since we operate on
daily bars over a multi-year backtest).

The source itself is intraday-1-minute-NQ-futures-specific; here it is
mechanically adapted to daily bars for this repo's equity/crypto loaders,
using a genuine recursive Kalman-filter implementation (constant-velocity
state-space model, not merely two EMAs) for both the fast and slow trend
estimates, and computing QTI as a rolling percentile rank of their percent
difference exactly per the source's own indicator construction.

This is the first Kalman-filter-based strategy tried in this repo --
distinct from all prior EMA/SMA/adaptive-MA (KAMA, FRAMA, McGinley, etc.)
trend constructions, which are non-recursive-state-space smoothers.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
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


def _kalman_trend(close: pd.Series, measurement_noise: float, process_noise: float = 1e-4) -> pd.Series:
    """Recursive 1D constant-velocity Kalman filter over price.

    State = [price, trend(velocity)]. Returns the filtered price estimate
    series. Higher `measurement_noise` (R) -> smoother/slower (trusts the
    model more); lower R -> tracks the raw observations more closely.
    """
    n = len(close)
    values = close.values.astype(float)
    est = np.zeros(n)
    # State: x = [price, velocity]; F = [[1,1],[0,1]]; H = [1, 0]
    x = np.array([values[0], 0.0])
    P = np.eye(2) * 1.0
    F = np.array([[1.0, 1.0], [0.0, 1.0]])
    H = np.array([[1.0, 0.0]])
    Q = np.eye(2) * process_noise
    R = np.array([[measurement_noise]])

    for i in range(n):
        # Predict
        x = F @ x
        P = F @ P @ F.T + Q
        # Update
        z = values[i]
        y = z - (H @ x)[0]
        S = (H @ P @ H.T)[0, 0] + R[0, 0]
        K = (P @ H.T) / S  # shape (2,1)
        x = x + (K.flatten() * y)
        P = (np.eye(2) - K @ H) @ P
        est[i] = x[0]
    return pd.Series(est, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    fast_r: float = 0.5,
    slow_r: float = 50.0,
    qti_lookback: int = 90,
    entry_level: float = 5.0,
    target_level: float = 35.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: rolling-percentile QTI (of fast-vs-slow Kalman filter pct
    difference) crosses above `entry_level`.
    Exit: QTI reaches `target_level` (profit target), OR QTI falls back
    below `entry_level` (stop), OR `max_hold_days` time-stop.
    """
    df = _prep(price_df)
    close = df["close"]

    fast = _kalman_trend(close, measurement_noise=fast_r)
    slow = _kalman_trend(close, measurement_noise=slow_r)
    pct_diff = (fast - slow) / slow.replace(0, np.nan) * 100.0

    # Rolling percentile rank in [-100, 100]: rescale the rolling rank
    # (0..1) of the current value within its own trailing window.
    def _pct_rank(window: pd.Series) -> float:
        if len(window) < 2:
            return 0.0
        current = window.iloc[-1]
        rank = (window < current).sum() / (len(window) - 1)
        return (rank * 200.0) - 100.0

    qti = pct_diff.rolling(qti_lookback, min_periods=max(10, qti_lookback // 3)).apply(
        _pct_rank, raw=False
    )

    entry_cross = (qti > entry_level) & (qti.shift(1) <= entry_level)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            q = qti.iloc[i]
            hit_target = (q is not None) and not pd.isna(q) and q >= target_level
            hit_stop = (q is not None) and not pd.isna(q) and q < entry_level
            if hit_target or hit_stop or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_cross.iloc[i]) if not pd.isna(entry_cross.iloc[i]) else False:
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
