"""Strategy: SMA(trend_window) directional gate with continuous TTM Trend
distance sizing overlay + deadband, leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-15-039, this cron trigger):
TTM Trend (John Carter, "Mastering the Trade") is a boolean trend classifier:
per VectorTA's docs (https://vectoralpha.dev/projects/ta/indicators/ttm_trend/,
visited this iteration) it compares close to a rolling SMA of hl2 (the
average of high/low, "average price") over a short window (default period=5):
bar is "up" when close > SMA(hl2, period), "down" otherwise.

This repo's prior TTM Trend entries (2026-09-10-080 accepted SPY-only plain
color-flip; 2026-09-10-091 rejected vol-gated variant) treated the indicator
as a DISCRETE binary color-flip trigger. This iteration reuses the identical
underlying construction -- close's distance from the rolling hl2-average --
but as a CONTINUOUS sizing dial rather than a binary flip, per this repo's
established rescue pattern (successfully applied to WaveTrend CI, McGinley
Dynamic, DSS Bressert, VSA effort/result, BW-MFI ROC, and others in recent
cron triggers): normalized distance = (close - SMA(hl2, period)) / SMA(hl2,
period), rolling z-scored and tanh-squashed into [-1,+1], used to scale
exposure up/down inside an SMA(trend_window) uptrend gate, with a deadband
to cut turnover. Distinct from 2026-09-10-080/091: continuous sizing dial
vs binary color-flip entry/exit, and no explicit vol-regime gate (091's vol
gate made things worse; this iteration instead lets the z-score/tanh
naturally scale down in calm/choppy stretches near the reference line).

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


def _ttm_trend_distance(df: pd.DataFrame, period: int) -> pd.Series:
    """Normalized distance of close from the rolling SMA(hl2, period)
    "average price" reference line used by TTM Trend's binary classifier.
    """
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]

    hl2 = (high + low) / 2.0
    reference = hl2.rolling(period).mean()
    distance = (close - reference) / reference.replace(0.0, np.nan)
    return distance


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
    ttm_period: int = 5,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    close's normalized distance from SMA(hl2, ttm_period) is rolling
    z-scored over `zscore_window` and tanh-squashed to [-1,+1] before use
    as a sizing dial, gated by an SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    distance = _ttm_trend_distance(df, ttm_period)

    roll_mean = distance.rolling(zscore_window).mean()
    roll_std = distance.rolling(zscore_window).std()
    zscore = (distance - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ttm_period: int = 5,
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
        ttm_period=ttm_period,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
