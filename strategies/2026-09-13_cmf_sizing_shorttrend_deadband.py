"""Strategy: SMA(short trend_window) trend-following gate with continuous
Chaikin Money Flow (CMF) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-13-090):
Chaikin Money Flow (Marc Chaikin) combines the Money Flow Multiplier --
MFM = ((Close-Low) - (High-Close)) / (High-Low), naturally bounded [-1, 1]
-- with volume: MFV = MFM * Volume, then CMF(n) = sum(MFV, n) / sum(Volume,
n), producing a naturally bounded [-1, 1] oscillator (this repo's own
Investopedia/StockCharts-derived formula, used consistently across 5+ prior
CMF entries, all of which used it as a binary zero-line/threshold ENTRY
signal, e.g. 2026-09-04-043/2026-09-05-047/2026-09-07-016). This iteration
applies CMF as a CONTINUOUS SIZING dial instead -- the same construction
validated 8x already this cron trigger for other bounded oscillators
(%B/Aroon/Williams%R/CMO/UO/RVI/StochRSI/MFI, 2026-09-13-071 through -089).
CMF is naturally bounded [-1,1] already (unlike MFI's [0,100] or the other
oscillators' varying ranges), so exposure scales linearly off CMF itself
rather than a (indicator-50)/50-style recentering. Distinct from
2026-09-13-089's MFI: MFI is a volume-weighted RSI-style ratio oscillator
built from Positive/Negative money flow SUMS (always positive quantities,
compressed through an RSI transform), while CMF is a volume-weighted AVERAGE
of a per-bar intrabar-range positioning term (Money Flow Multiplier,
symmetric and can be exactly zero or negative), a fundamentally different
volume-weighting mechanism. Built with the shortened trend_window and
deadband already validated this cron trigger, applied from the outset.

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


def _cmf(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Chaikin Money Flow, naturally bounded [-1, 1]."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)

    range_ = (high - low).replace(0, np.nan)
    money_flow_multiplier = ((close - low) - (high - close)) / range_
    money_flow_volume = money_flow_multiplier * volume

    cmf = money_flow_volume.rolling(window).sum() / volume.rolling(window).sum().replace(0, np.nan)
    return cmf.clip(lower=-1.0, upper=1.0)


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
    cmf_window: int = 20,
    base_exposure: float = 0.8,
    cmf_sensitivity: float = 0.8,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    cmf = _cmf(df, window=cmf_window)

    raw_exposure = base_exposure + cmf_sensitivity * cmf
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    cmf_window: int = 20,
    base_exposure: float = 0.8,
    cmf_sensitivity: float = 0.8,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        cmf_window=cmf_window,
        base_exposure=base_exposure,
        cmf_sensitivity=cmf_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
