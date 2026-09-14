"""Strategy: SMA(trend_window) directional gate with continuous Kairi
Relative Index (range-position variant) sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
This repo's only prior Kairi Relative Index entry (2026-09-04-167) used the
SMA-deviation construction (KRI=100*(close-SMA)/SMA, unbounded) as a binary
oversold-threshold mean-reversion entry, REJECTED. Per
https://tradingbrokers.com/kairi-relative-index/ there is a second,
distinct KRI construction: a range-position oscillator naturally bounded
[-100,+100] by construction:

    KRI = ((CurrentPrice - LowestPrice) - (HighestPrice - CurrentPrice))
          / (HighestPrice - LowestPrice) * 100
        = (2*CurrentPrice - HighestPrice - LowestPrice)
          / (HighestPrice - LowestPrice) * 100

(HighestPrice/LowestPrice = rolling max/min of close over `period`; +100 =
price at the top of its recent range, -100 = bottom). This iteration uses
this range-position KRI as a CONTINUOUS SIZING dial within an
SMA(trend_window) uptrend gate -- first KRI-as-continuous-sizing-dial
variant, and the first use of this range-position (rather than
SMA-deviation) KRI construction in this repo at all.

Source: https://tradingbrokers.com/kairi-relative-index/

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


def _kri(close: pd.Series, period: int) -> pd.Series:
    highest = close.rolling(period).max()
    lowest = close.rolling(period).min()
    rng = (highest - lowest).replace(0.0, np.nan)
    kri = (2.0 * close - highest - lowest) / rng * 100.0
    return kri.fillna(0.0).clip(lower=-100.0, upper=100.0)


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
    period: int = 14,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    KRI is bounded [-100,100] by construction; rescaled to [-1,+1] via
    /100, then used directly as a sizing dial within the
    SMA(trend_window) uptrend gate.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    kri = _kri(close, period)
    kri_centered = kri / 100.0

    raw_exposure = base_exposure + sensitivity * kri_centered
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    period: int = 14,
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
        period=period,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
