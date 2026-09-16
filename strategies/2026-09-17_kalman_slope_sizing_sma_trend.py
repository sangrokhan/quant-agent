"""Strategy: SMA(trend_window) directional gate with continuous Kalman-filter
trend-slope sizing overlay + deadband, leverage-cap-aware for crypto from the
start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per Quantitativo's "Fast trend following" (https://www.quantitativo.com/p/fast-trend-following,
read this iteration): a single constant-velocity 1D Kalman filter (level +
slope state, process/measurement noise ratio tuned by a single Q/R ratio
parameter) applied to close price gives a smoother, lower-lag trend estimate
than a moving average, and the filter's own estimated SLOPE state is a
naturally continuous trend-strength/direction signal (not just the binary
"price above/below the filter level" crossover already tested twice in this
repo: 2026-09-05-056 dual-Kalman percentile-breakout rejected;
2026-09-08-052 single Kalman level+slope binary crossover -- also already
tested). This sub-iteration reframes the SAME Kalman level+slope filter as a
CONTINUOUS SIZING dial: the filter's normalized slope (slope / rolling ATR,
z-scored, tanh-squashed) scales exposure smoothly within an SMA(trend_window)
uptrend gate, following this repo's now-established and repeatedly
successful "binary oscillator -> continuous sizing dial" rescue pattern
(applied previously to DPO, Hurst, VHF, TII, RVI, MAMA-FAMA spread, etc.)
First Kalman-filter-slope-as-continuous-sizing-dial strategy in this repo
(0 prior entries of this exact construction, confirmed via
knowledge_base/strategies_index.jsonl grep for "Kalman" -- 8 prior hits, all
binary crossover/breakout/mean-reversion triggers, none a continuous dial).

Kalman filter construction (constant-velocity model, standard textbook
formulation, e.g. per theforexgeek.com's "Kalman Filter Trading Strategy"
already cited in 2026-09-08-052, re-confirmed via Quantitativo's own
description of a "level + slope" state Kalman filter for trend estimation):
    State: x = [level, slope]
    Transition: level_t = level_{t-1} + slope_{t-1}; slope_t = slope_{t-1}
    Process noise Q (scaled by q_var), Measurement noise R (scaled by r_var)
    Standard predict/update recursion, no external library required.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
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


def _kalman_level_slope(close: pd.Series, q_var: float, r_var: float):
    """Constant-velocity 1D Kalman filter over price. Returns (level, slope)
    as pandas Series aligned to `close`'s index.

    State vector x = [level, slope]; transition matrix F = [[1,1],[0,1]];
    measurement matrix H = [1, 0] (we only observe price/level directly).
    Q = q_var * I (process noise), R = r_var (scalar measurement noise).
    """
    values = close.to_numpy(dtype=float)
    n = len(values)
    levels = np.zeros(n)
    slopes = np.zeros(n)

    # State and covariance init
    x = np.array([values[0], 0.0])
    P = np.eye(2) * 1.0

    F = np.array([[1.0, 1.0], [0.0, 1.0]])
    H = np.array([[1.0, 0.0]])
    Q = np.eye(2) * q_var
    R = np.array([[r_var]])

    levels[0] = x[0]
    slopes[0] = x[1]

    for i in range(1, n):
        # Predict
        x = F @ x
        P = F @ P @ F.T + Q

        # Update
        z = values[i]
        y = z - (H @ x)[0]
        S = (H @ P @ H.T)[0, 0] + R[0, 0]
        K = (P @ H.T).flatten() / S if S != 0 else np.zeros(2)
        x = x + K * y
        P = (np.eye(2) - np.outer(K, H)) @ P

        levels[i] = x[0]
        slopes[i] = x[1]

    idx = close.index
    return pd.Series(levels, index=idx), pd.Series(slopes, index=idx)


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    q_var: float = 0.01,
    r_var: float = 1.0,
    zscore_window: int = 60,
    sensitivity: float = 0.6,
    base_exposure: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    The Kalman filter's estimated slope is rolling-z-scored (over
    zscore_window) and tanh-squashed to bound it to roughly [-1,1], then
    used as a sizing dial: exposure = clip(base_exposure +
    sensitivity*dial, 0, cap), gated to 0 whenever close is below its
    SMA(trend_window).
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    _level, slope = _kalman_level_slope(close, q_var=q_var, r_var=r_var)

    roll_mean = slope.rolling(zscore_window).mean()
    roll_std = slope.rolling(zscore_window).std(ddof=0)
    z = (slope - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(z.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    q_var: float = 0.01,
    r_var: float = 1.0,
    zscore_window: int = 60,
    sensitivity: float = 0.6,
    base_exposure: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        q_var=q_var,
        r_var=r_var,
        zscore_window=zscore_window,
        sensitivity=sensitivity,
        base_exposure=base_exposure,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
