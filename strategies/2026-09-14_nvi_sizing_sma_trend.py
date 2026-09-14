"""Strategy: SMA(trend_window) directional gate with continuous Negative
Volume Index (NVI) sizing overlay + deadband, leverage-cap-aware for crypto
from the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Negative Volume Index (Paul Dysart / Norman Fosback): a cumulative index
that only updates on days when volume DECREASES vs the prior day, adding
that day's % price change ("smart money" tracking theory -- big informed
moves happen on quiet, low-volume days). Formula confirmed via Google AI
overview (browser_exec fallback -- web_search DDGS backend returned a TLS
connection error for this query): NVI_t = NVI_{t-1} + (P_t-P_{t-1})/P_{t-1}
* NVI_{t-1} if V_t < V_{t-1}, else NVI_t = NVI_{t-1} (unchanged). Repo has
exactly 1 prior NVI entry (2026-09-04-139: NVI-crosses-its-255d-MA binary
crossover confirmed by a long trend filter, REJECTED decisively across
equity+crypto).

This iteration is distinct from 2026-09-04-139 in mechanism, not just
parameters: rather than a binary MA-crossover trigger, it converts NVI's
own SHORT-HORIZON rate of change (pct_change over roc_window, capturing
how fast "smart money" volume-quiet accumulation/distribution is moving)
into a rolling z-score, then uses that z-score as a CONTINUOUS SIZING dial
layered on top of a SMA(trend_window) long/flat directional gate -- the
same continuous-sizing-dial + deadband + leverage-cap-aware-for-crypto
pattern already validated broadly across 15+ other indicator families this
cron trigger (e.g. 2026-09-14-122 Chaikin Oscillator, -126 Demand Index,
-128 Klinger Volume Oscillator). Testing whether NVI's smart-money-timing
signal, which failed as a discrete crossover trigger, works better as a
smooth conviction/exposure dial instead.

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


def _negative_volume_index(df: pd.DataFrame, base_value: float = 1000.0) -> pd.Series:
    """Cumulative NVI: updates only on volume-decrease days (Fosback)."""
    close, volume = df["close"], df["volume"]
    pct_change = close.pct_change().fillna(0.0)
    vol_decreased = volume < volume.shift(1)

    nvi = np.empty(len(df))
    nvi[:] = np.nan
    current = base_value
    for i in range(len(df)):
        if i == 0:
            nvi[i] = base_value
            continue
        if bool(vol_decreased.iloc[i]):
            current = current + pct_change.iloc[i] * current
        nvi[i] = current
    return pd.Series(nvi, index=df.index)


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
    roc_window: int = 10,
    zscore_window: int = 90,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    nvi = _negative_volume_index(df)
    nvi_roc = nvi.pct_change(roc_window)
    nvi_mean = nvi_roc.rolling(zscore_window).mean()
    nvi_std = nvi_roc.rolling(zscore_window).std().replace(0, np.nan)
    nvi_zscore = ((nvi_roc - nvi_mean) / nvi_std).clip(lower=-2.5, upper=2.5)

    raw_exposure = base_exposure + sensitivity * (nvi_zscore / 2.5)
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    roc_window: int = 10,
    zscore_window: int = 90,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
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
