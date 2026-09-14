"""Strategy: SMA(trend_window) directional gate with continuous Chaikin
Oscillator (rolling z-score normalized) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Chaikin Oscillator (Marc Chaikin; formula per
https://www.investopedia.com/terms/c/chaikinoscillator.asp, read this
iteration via browser_exec fallback -- web_search's DuckDuckGo backend
TLS-errored on every query attempted this iteration): Money Flow
Multiplier N = ((Close-Low)-(High-Close))/(High-Low); Money Flow Volume
M = N * Volume; Accumulation/Distribution Line ADL = cumulative sum of M;
Chaikin Oscillator CO = EMA(ADL, 3) - EMA(ADL, 10) -- momentum of the
volume-weighted accumulation/distribution line.

This repo has 2 prior Chaikin Oscillator entries (2026-09-04-093 zero-line
crossover with SMA200 trend filter; 2026-09-09-068 hidden bullish
divergence), BOTH using CO as a binary threshold/crossover/divergence
ENTRY trigger -- both rejected. Neither reframed CO as a CONTINUOUS SIZING
dial (the pattern that rescued CMO/UO/StochRSI/MFI/CMF/Aroon/Williams%R/
%B/DMI-diff/ADX/CHOP/ER/TRIX/TSI/R2/Elder-Ray-net-power this cron
trigger). CO is dollar*volume-scale (not natively bounded), so unlike this
iteration's own recent ATR-normalization for Elder-Ray net power
(2026-09-14-121), here CO is normalized via a rolling z-score
(co_zscore = (CO - rolling_mean(CO, zscore_window)) /
rolling_std(CO, zscore_window)) -- a distinct normalization technique not
yet applied to any prior sizing-dial strategy in this repo, testing
whether relative (z-scored) rather than absolute (ATR-scaled) volume-flow
momentum improves the sizing signal. Within an SMA(trend_window) uptrend
gate, exposure scales up as z-scored CO strengthens and toward the base
level as it fades, rather than using CO threshold/crossovers/divergence as
a hard binary trigger.

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


def _chaikin_oscillator(df: pd.DataFrame, fast: int = 3, slow: int = 10) -> pd.Series:
    """CO = EMA(ADL, fast) - EMA(ADL, slow).

    ADL = cumulative sum of Money Flow Volume (Money Flow Multiplier *
    Volume), where Money Flow Multiplier N = ((Close-Low)-(High-Close)) /
    (High-Low), bounded [-1, 1] by construction.
    """
    high, low, close, volume = df["high"], df["low"], df["close"], df["volume"]
    range_ = (high - low).replace(0, np.nan)
    mf_multiplier = ((close - low) - (high - close)) / range_
    mf_volume = mf_multiplier.fillna(0.0) * volume
    adl = mf_volume.cumsum()

    co = adl.ewm(span=fast, adjust=False).mean() - adl.ewm(span=slow, adjust=False).mean()
    return co


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
    co_fast: int = 3,
    co_slow: int = 10,
    zscore_window: int = 60,
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
    co = _chaikin_oscillator(df, fast=co_fast, slow=co_slow)
    co_mean = co.rolling(zscore_window).mean()
    co_std = co.rolling(zscore_window).std().replace(0, np.nan)
    co_zscore = ((co - co_mean) / co_std).clip(lower=-2.5, upper=2.5)

    raw_exposure = base_exposure + sensitivity * (co_zscore / 2.5)
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    co_fast: int = 3,
    co_slow: int = 10,
    zscore_window: int = 60,
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
        co_fast=co_fast,
        co_slow=co_slow,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
