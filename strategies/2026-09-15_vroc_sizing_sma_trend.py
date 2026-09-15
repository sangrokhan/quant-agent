"""Strategy: SMA(trend_window) directional gate with continuous Volume Rate
of Change (VROC) sizing overlay + deadband, leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-15-041, this cron trigger):
Volume Rate of Change (VROC), per UEEx's blog explainer
(https://blog.ueex.com/volume-rate-of-change-vroc/, already visited/logged
in this repo's knowledge base from a prior iteration -- id 2026-09-12-140 --
so not re-fetched this iteration per the visited-pages dedupe ledger):
VROC = [(current volume - volume N periods ago) / volume N periods ago] * 100.

This repo's prior VROC entries (2026-09-12-140, VROC>=threshold as a
discrete Donchian-breakout confirmation gate, rejected 0/54 crypto, weak
equity Sharpe) treated VROC as a binary threshold trigger. This iteration
reuses the identical underlying construction -- volume's own rate of
change, not a dollar-flow/typical-price volume oscillator like MFI/Klinger
-- but as a CONTINUOUS sizing dial rather than a discrete confirmation
gate, per this cron trigger's established rescue pattern: VROC is rolling
z-scored and tanh-squashed into [-1,+1], used to scale exposure up/down
(rising volume interest = higher conviction = larger position) inside an
SMA(trend_window) uptrend gate, with a deadband to cut turnover. Distinct
from 2026-09-12-140 (discrete Donchian-breakout confirmation gate vs
continuous trend-following sizing dial with no breakout-entry mechanic).

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


def _vroc(df: pd.DataFrame, vroc_window: int) -> pd.Series:
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)
    volume_lag = volume.shift(vroc_window)
    vroc = (volume - volume_lag) / volume_lag.replace(0.0, np.nan) * 100.0
    return vroc


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
    vroc_window: int = 14,
    smooth_window: int = 5,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    VROC is smoothed over `smooth_window` bars, rolling z-scored over
    `zscore_window`, and tanh-squashed to [-1,+1] before use as a sizing
    dial, gated by an SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    vroc = _vroc(df, vroc_window)
    vroc_smoothed = vroc.rolling(smooth_window).mean()

    roll_mean = vroc_smoothed.rolling(zscore_window).mean()
    roll_std = vroc_smoothed.rolling(zscore_window).std()
    zscore = (vroc_smoothed - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    vroc_window: int = 14,
    smooth_window: int = 5,
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
        vroc_window=vroc_window,
        smooth_window=smooth_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
