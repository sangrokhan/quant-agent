"""Strategy: SMA(trend_window) directional gate with continuous
Accumulation/Distribution Line (ADL) rate-of-change sizing overlay +
deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Accumulation/Distribution Line (A/D Line, Marc Chaikin): a cumulative
volume-flow indicator using the Close-Location Value (CLV) to weight each
bar's volume:
    MFM_t = ((Close_t-Low_t) - (High_t-Close_t)) / (High_t-Low_t)
    ADL_t = ADL_{t-1} + MFM_t * Volume_t
This repo has 3 prior ADL-family entries (2026-09-06-138/2026-09-09-026
bullish divergence, accepted; and the derived Chaikin Oscillator --
EMA(ADL,3)-EMA(ADL,10) -- already tested as continuous sizing,
2026-09-14-122, QQQ/SPY accepted but crypto rejected on decisive MDD).
This iteration is distinct: rather than the Chaikin Oscillator's short-vs-
long EMA spread of ADL, this uses the RAW ADL line's own rolling rate of
change (diff over `roc_window` bars -- the same technique validated this
cron trigger for OBV/PVT, 2026-09-14-151/-152), rolling z-scored and
tanh-squashed to [-1,+1], sized within an SMA(trend_window) uptrend gate.
First raw-ADL (not Chaikin-Oscillator-derived) continuous-sizing variant in
this repo.

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


def _adl(df: pd.DataFrame) -> pd.Series:
    """Cumulative Accumulation/Distribution Line."""
    high, low, close, volume = df["high"], df["low"], df["close"], df["volume"]
    range_ = (high - low).replace(0.0, np.nan)
    mfm = ((close - low) - (high - close)) / range_
    mfm = mfm.fillna(0.0)
    return (mfm * volume).cumsum()


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

    Raw ADL's own rolling `roc_window`-bar rate of change is rolling
    z-scored over `zscore_window` bars and tanh-squashed to [-1,+1] before
    use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    adl = _adl(df)
    adl_roc = adl.diff(roc_window)
    roll_mean = adl_roc.rolling(zscore_window).mean()
    roll_std = adl_roc.rolling(zscore_window).std()
    zscore = (adl_roc - roll_mean) / roll_std.replace(0.0, np.nan)
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
