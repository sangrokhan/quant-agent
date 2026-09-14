"""Strategy: SMA(trend_window) directional gate with continuous Time
Segmented Volume (TSV) sizing overlay + deadband, leverage-cap-aware for
crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Time Segmented Volume (TSV, Worden Brothers, TC2000): a rolling sum of
volume-weighted price change,
    TV_i = Volume_i * (Close_i - Close_{i-1})
    TSV_n = sum(TV_i for i in [n-L+1, n])
a money-flow oscillator distinct from OBV/CMF/MFI in this repo's already-
tested volume family since it uses the raw price DELTA (not just its sign)
weighted by volume, summed over a rolling window (not smoothed via EMA).
Formula confirmed via Google AI-overview synthesis of
Investopedia/TC2000/useThinkScript (browser_exec fallback).

This repo has 1 prior TSV entry (2026-09-06-165, a binary TSV-crosses-its-
own-signal-SMA crossover, decisively rejected). This iteration reframes TSV
as a CONTINUOUS SIZING dial: the raw unbounded TSV sum, rolling z-scored and
tanh-squashed to [-1,+1], used as a sizing multiplier within an
SMA(trend_window) uptrend gate -- distinct mechanism (continuous dial vs
binary crossover) from the prior rejected attempt, following this cron
trigger's validated continuous-sizing-dial pattern.

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


def _tsv(close: pd.Series, volume: pd.Series, tsv_window: int) -> pd.Series:
    """Rolling sum of volume-weighted price change over `tsv_window` bars."""
    tv = volume * close.diff()
    return tv.rolling(tsv_window).sum()


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
    tsv_window: int = 13,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Raw TSV is unbounded (scales with price/volume magnitude), so it's
    rolling-z-scored over `zscore_window` bars and tanh-squashed to [-1,+1]
    before use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    trend_long = close > close.rolling(trend_window).mean()
    tsv = _tsv(close, volume, tsv_window)
    roll_mean = tsv.rolling(zscore_window).mean()
    roll_std = tsv.rolling(zscore_window).std()
    zscore = (tsv - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    tsv_window: int = 13,
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
        tsv_window=tsv_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
