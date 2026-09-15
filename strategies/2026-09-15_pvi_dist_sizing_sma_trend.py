"""Strategy: SMA(trend_window) directional gate with continuous Positive
Volume Index (PVI) rate-of-change sizing overlay + deadband,
leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-15-043, this cron trigger):
Positive Volume Index (PVI, Norman Fosback / classic HPotter construction,
formula already documented in this repo from a prior iteration --
2026-09-05-001 -- and its already-visited sources, not re-fetched this
iteration per the dedupe ledger): cumulative sum of daily price %-change,
added only on days where volume INCREASED vs the prior day (days with flat
or declining volume leave PVI unchanged). This repo's prior PVI entry
(2026-09-05-001) used PVI crossing above its own N-period moving average
as a discrete crossover trigger and was a near-miss rejection (QQQ close).
This iteration reuses the identical underlying construction -- volume-
increase-conditioned cumulative price momentum -- but as a CONTINUOUS
sizing dial rather than a binary crossover, per this cron trigger's
established rescue pattern: the smoothed rate-of-change of PVI relative to
its own moving average is rolling z-scored and tanh-squashed into [-1,+1],
used to scale exposure up/down inside an SMA(trend_window) uptrend gate,
with a deadband. Distinct from 2026-09-05-001 (discrete MA-crossover
trigger vs continuous distance-based sizing dial).

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


def _pvi(df: pd.DataFrame) -> pd.Series:
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)

    pct_change = close.pct_change().fillna(0.0)
    volume_increased = volume > volume.shift(1)

    pvi = np.zeros(len(df))
    pvi[0] = 1000.0
    for t in range(1, len(df)):
        if bool(volume_increased.iloc[t]):
            pvi[t] = pvi[t - 1] * (1.0 + pct_change.iloc[t])
        else:
            pvi[t] = pvi[t - 1]
    return pd.Series(pvi, index=df.index)


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
    pvi_ma_window: int = 30,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Normalized distance of PVI from its own SMA(pvi_ma_window) is rolling
    z-scored over `zscore_window` and tanh-squashed to [-1,+1] before use
    as a sizing dial, gated by an SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    pvi = _pvi(df)
    pvi_ma = pvi.rolling(pvi_ma_window).mean()
    distance = (pvi - pvi_ma) / pvi_ma.replace(0.0, np.nan)

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
    pvi_ma_window: int = 30,
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
        pvi_ma_window=pvi_ma_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
