"""Strategy: SMA(trend_window) directional gate with continuous Price and
Volume Trend (PVT) rate-of-change sizing overlay + deadband, leverage-cap-
aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Price and Volume Trend (PVT): a cumulative volume indicator that, unlike
OBV's simple +/-full-volume step, scales each bar's volume by that day's
PERCENTAGE price change:
    PVT_t = PVT_{t-1} + Volume_t * (Close_t - Close_{t-1}) / Close_{t-1}
This repo has 2 prior PVT entries (2026-09-04-101, 2026-09-09-095), both
binary PVT-vs-own-EMA-signal-line crossover triggers. Since raw PVT is a
cumulative running total (unbounded, nonstationary over the sample -- the
same issue as OBV, already addressed this cron trigger via 2026-09-14-151's
rate-of-change reframing), this iteration applies the identical technique to
PVT: its own rolling rate of change (diff over `roc_window` bars), rolling
z-scored and tanh-squashed to [-1,+1], used as a sizing multiplier within an
SMA(trend_window) uptrend gate. First PVT continuous-sizing variant in this
repo.

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


def _pvt(close: pd.Series, volume: pd.Series) -> pd.Series:
    """Cumulative Price and Volume Trend: cumsum(volume * pct_change(close))."""
    pct_change = close.pct_change().fillna(0.0)
    return (volume * pct_change).cumsum()


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
    roc_window: int = 20,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    PVT's own rolling `roc_window`-bar rate of change (a diff, since PVT can
    cross zero) is rolling-z-scored over `zscore_window` bars and
    tanh-squashed to [-1,+1] before use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    trend_long = close > close.rolling(trend_window).mean()
    pvt = _pvt(close, volume)
    pvt_roc = pvt.diff(roc_window)
    roll_mean = pvt_roc.rolling(zscore_window).mean()
    roll_std = pvt_roc.rolling(zscore_window).std()
    zscore = (pvt_roc - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    roc_window: int = 20,
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
        roc_window=roc_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
