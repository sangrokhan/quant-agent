"""Strategy: SMA(short trend_window) trend-following gate with continuous
Volume Zone Oscillator (VZO) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-13-091):
Volume Zone Oscillator (Khalil & Steckler 2009/2011): VZO = 100*(VP/TV),
where VP = EMA of signed (OBV-style, +volume on up-close days / -volume on
down-close days) volume, TV = EMA of raw (unsigned) volume -- roughly
bounded in [-100, 100] in practice (this repo's own formula from
2026-09-04-122/2026-09-10-115, no new external source needed this
iteration). This repo's 2 prior VZO entries used it as a rare
threshold-crossing ENTRY trigger (-40% oversold recovery, or zero-line
cross) and BOTH were decisively rejected -- 2026-09-04-122 specifically
noted only 9 trades over 7.5 years, "too rare an event to build a reliable
edge at daily-bar resolution." This iteration instead applies VZO as a
CONTINUOUS SIZING dial (the construction validated 9x already this cron
trigger for other bounded oscillators, most recently CMF-090 and MFI-089),
sidestepping the "too rare" problem entirely since sizing responds to VZO's
value every day rather than waiting for a threshold crossing. Distinct from
both MFI (RSI-style ratio of flow sums) and CMF (volume-weighted average of
an intrabar-positioning term): VZO normalizes SIGNED OBV-style volume by
TOTAL volume via dual EMAs, a third distinct volume-weighting mechanism.

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


def _vzo(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """Volume Zone Oscillator, VZO = 100 * VP / TV."""
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)

    signed_volume = volume.where(close.diff() >= 0, -volume)
    vp = signed_volume.ewm(span=window, adjust=False).mean()
    tv = volume.ewm(span=window, adjust=False).mean()

    vzo = 100.0 * vp / tv.replace(0, np.nan)
    return vzo


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
    vzo_window: int = 14,
    base_exposure: float = 0.8,
    vzo_sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    vzo = _vzo(df, window=vzo_window)

    raw_exposure = base_exposure + vzo_sensitivity * (vzo / 40.0)
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    vzo_window: int = 14,
    base_exposure: float = 0.8,
    vzo_sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        vzo_window=vzo_window,
        base_exposure=base_exposure,
        vzo_sensitivity=vzo_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
