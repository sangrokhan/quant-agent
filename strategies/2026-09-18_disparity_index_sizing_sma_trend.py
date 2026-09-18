"""Strategy: SMA(trend_window) directional gate with continuous Disparity
Index distance-from-MA sizing overlay + deadband, leverage-cap-aware for
crypto from the start.

Hypothesis (this cron trigger):
Disparity Index = 100*(close-SMA)/SMA, per GoCharting's Disparity Index
docs (formula already on file in this repo from 2026-09-06-140, not
re-fetched this iteration). This repo's prior Disparity Index entry
(2026-09-06-140) used a BINARY extreme-threshold mean-reversion trigger
(entry only when DI hits a fixed negative extreme, exit on reversion to
zero): rejected, with a near-miss confined to QQQ's mid-vol tercile only.

This iteration reframes Disparity Index as a CONTINUOUS SIZING dial
(rolling z-scored + tanh-squashed to [-1,1]) used as an exposure multiplier
inside an SMA(trend_window) uptrend gate + deadband -- the pattern that has
rescued many other binary near-miss/narrow-regime indicators in this repo
(VAMA, DPO, Hurst, VHF, TII, RVI, MAMA-FAMA spread, Kalman slope, CBOE SKEW,
VPT, McGinley Dynamic, T3). First Disparity Index continuous-sizing variant
in this repo.

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


def _disparity_index(close: pd.Series, sma_window: int) -> pd.Series:
    sma = close.rolling(sma_window).mean()
    return 100.0 * (close - sma) / sma.replace(0.0, np.nan)


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
    di_sma_window: int = 14,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Disparity Index (100*(close-SMA)/SMA) is rolling z-scored and
    tanh-squashed to [-1,1], then used as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    di = _disparity_index(close, di_sma_window)

    roll_mean = di.rolling(zscore_window).mean()
    roll_std = di.rolling(zscore_window).std().replace(0.0, np.nan)
    z = (di - roll_mean) / roll_std
    dial = np.tanh(z.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    di_sma_window: int = 14,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        di_sma_window=di_sma_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
