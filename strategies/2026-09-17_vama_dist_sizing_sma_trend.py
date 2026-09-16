"""Strategy: SMA(trend_window) directional gate with continuous Volatility
Adjusted Moving Average (VAMA) distance-from-baseline sizing overlay +
deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Volatility Adjusted Moving Average (VAMA), per
https://pineify.app/resources/blog/volatility-adjusted-moving-average-indicator-tradingview-pine-script
(formula already confirmed in this repo from 2026-09-08-036, not re-fetched
this iteration per dedupe rule): scales a baseline EMA multiplicatively by
a High-Low-range-relative-to-EMA volatility ratio: VolRatio =
(HighestHigh(vol_lookback) - LowestLow(vol_lookback)) / EMA(close, length);
VAMA = EMA(close, length) * (1 + VolRatio * sensitivity_factor).

This repo's prior VAMA entry (2026-09-08-036) used a binary breakout +
slope-confirmation trigger: accepted QQQ only, SPY was a near-miss (Sharpe
0.974, all else passing), crypto rejected decisively. This iteration
reframes VAMA as a CONTINUOUS SIZING dial (distance of close from its own
VAMA baseline, rolling z-scored + tanh-squashed to [-1,1]) used as an
exposure multiplier inside an SMA(trend_window) uptrend gate + deadband --
the pattern that has rescued many other adaptive-MA-distance near-misses in
this repo (FRAMA, KAMA-style, T3, DPO). First VAMA continuous-sizing
variant.

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


def _vama(high: pd.Series, low: pd.Series, close: pd.Series, length: int, vol_lookback: int, sensitivity_factor: float) -> pd.Series:
    ema = close.ewm(span=length, adjust=False).mean()
    highest_high = high.rolling(vol_lookback).max()
    lowest_low = low.rolling(vol_lookback).min()
    vol_ratio = (highest_high - lowest_low) / ema.replace(0.0, np.nan)
    vama = ema * (1 + vol_ratio * sensitivity_factor)
    return vama


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
    vama_length: int = 14,
    vol_lookback: int = 10,
    vama_sensitivity_factor: float = 1.0,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Distance of close from its own VAMA baseline ((close-VAMA)/VAMA) is
    rolling z-scored and tanh-squashed to [-1,1], then used as a sizing dial.
    """
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    vama = _vama(high, low, close, vama_length, vol_lookback, vama_sensitivity_factor)
    dist = (close - vama) / vama.replace(0.0, np.nan)

    roll_mean = dist.rolling(zscore_window).mean()
    roll_std = dist.rolling(zscore_window).std().replace(0.0, np.nan)
    z = (dist - roll_mean) / roll_std
    dial = np.tanh(z.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    vama_length: int = 14,
    vol_lookback: int = 10,
    vama_sensitivity_factor: float = 1.0,
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
        vama_length=vama_length,
        vol_lookback=vol_lookback,
        vama_sensitivity_factor=vama_sensitivity_factor,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
