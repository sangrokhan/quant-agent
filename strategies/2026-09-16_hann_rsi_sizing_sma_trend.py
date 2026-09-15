"""Strategy: Ehlers Hann-windowed RSI (RSIH, TASC Jan 2022) reframed as a
CONTINUOUS SIZING dial within an SMA(trend_window) uptrend gate,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Direct fix for prior id 2026-09-12-148 (Hann-windowed RSI centerline
crossover: QQQ Sharpe 0.739/MDD 0.277 fail, SPY Sharpe 0.343/TC 0.284
fail, crypto decisively rejected 0/54; notes explicitly flagged extreme
vol-regime dependence -- strong low-vol edge that vanished/reversed in
mid-vol). This sub-iteration reframes hann_rsi (Wilder's classic
closes-up/closes-down RSI inputs smoothed with a Hann-window FIR filter,
already naturally bounded [-1,+1] by construction: hann_rsi =
(filtered_CU - filtered_CD)/(filtered_CU + filtered_CD)) as a CONTINUOUS
SIZING dial (used directly, no z-score/tanh needed since already bounded)
inside an SMA(trend_window) uptrend gate with a deadband, leverage-cap-
aware for crypto from the start -- this repo's established pattern for
rescuing binary-crossover rejections where the underlying oscillator
value itself may carry more graduated information than a hard 0-centerline
cross captures. Source unchanged from 2026-09-12-148
(https://www.tradingview.com/scripts/tasc/page-3/, TASC 2022.01 Improved
RSI w/Hann, John F. Ehlers). No new external research this sub-iteration.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _hann_weights(length: int) -> np.ndarray:
    k = np.arange(1, length + 1)
    w = 1.0 - np.cos(2.0 * math.pi * k / (length + 1))
    return w / w.sum()


def _hann_rsi(close: pd.Series, length: int) -> pd.Series:
    delta = close.diff().fillna(0.0)
    cu = delta.clip(lower=0.0)
    cd = (-delta).clip(lower=0.0)

    weights = _hann_weights(length)
    cu_vals = cu.to_numpy()
    cd_vals = cd.to_numpy()
    n = len(cu_vals)

    filtered_cu = np.zeros(n)
    filtered_cd = np.zeros(n)
    for t in range(n):
        if t < length:
            continue
        window_cu = cu_vals[t - length + 1 : t + 1][::-1]
        window_cd = cd_vals[t - length + 1 : t + 1][::-1]
        filtered_cu[t] = np.dot(weights, window_cu)
        filtered_cd[t] = np.dot(weights, window_cd)

    denom = filtered_cu + filtered_cd
    hann_rsi = np.where(denom != 0, (filtered_cu - filtered_cd) / np.where(denom != 0, denom, 1.0), 0.0)
    return pd.Series(hann_rsi, index=close.index)


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
    length: int = 14,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    hann_rsi (already bounded [-1,+1] by construction) is used directly as
    the sizing dial -- no z-score/tanh transform needed.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    hann_rsi = _hann_rsi(close, length)

    raw_exposure = base_exposure + sensitivity * hann_rsi
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    length: int = 14,
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
        length=length,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
