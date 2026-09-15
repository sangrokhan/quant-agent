"""Strategy: Ehlers Laguerre Oscillator (TASC July 2025) used as a
CONTINUOUS SIZING dial (z-score + tanh, since it's an unbounded
RMS-normalized spread, not a naturally [-1,1]-bounded value) within an
SMA(trend_window) uptrend gate, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per traders.com's exact disclosed EasyLanguage source (TASC July 2025
Traders' Tips, "Laguerre Filters" by John F. Ehlers,
https://traders.com/Documentation/FEEDbk_docs/2025/07/TradersTips.html,
visited this iteration via a systematic browser_exec scan of the TASC
Traders' Tips archive -- web_search failed/returned no useful results for
prior discovery queries this iteration): the Laguerre Oscillator is
distinct from this repo's already-tested Laguerre Filter (5-tap FIR
trend-following line) and Laguerre RSI (RSI computed on Laguerre-filtered
price). Construction:
    L0 = UltimateSmoother(close, length)      (Ehlers' low-lag smoother)
    L1 = -gamma*L0 + L0.shift(1) + gamma*L1.shift(1)   (single-stage
                                                          Laguerre recursion)
    RMS = sqrt(rolling_mean((L0-L1)^2, rms_window))
    LaguerreOsc = (L0 - L1) / RMS
a zero-line-crossing oscillator (roughly zero-centered but unbounded,
unlike several other recently-tested Ehlers indicators that are naturally
[-1,1]-bounded) measuring the instantaneous rate-of-change of the
UltimateSmoother relative to its own recent RMS volatility. Because it is
NOT naturally bounded, this strategy follows this repo's established
z-score + tanh-squash continuous-sizing pattern (same as VWMACD histogram,
PGO, BRAR, etc.) rather than a direct rescale.

First Laguerre Oscillator strategy in this repo.

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


def _ultimate_smoother(src: pd.Series, period: int) -> pd.Series:
    """Ehlers' UltimateSmoother (TASC Apr 2024): allpass minus highpass."""
    period = max(int(period), 1)
    a1 = math.exp(-1.414 * math.pi / period)
    c2 = 2.0 * a1 * math.cos(1.414 * math.pi / period)
    c3 = -a1 * a1
    c1 = (1.0 + c2 - c3) / 4.0

    vals = src.ffill().fillna(0.0).to_numpy()
    n = len(vals)
    us = np.zeros(n)
    for i in range(n):
        if i < 4:
            us[i] = vals[i]
        else:
            us[i] = (
                (1.0 - c1) * vals[i]
                + (2.0 * c1 - c2) * vals[i - 1]
                - (c1 + c3) * vals[i - 2]
                + c2 * us[i - 1]
                + c3 * us[i - 2]
            )
    return pd.Series(us, index=src.index)


def _laguerre_oscillator(
    close: pd.Series, gamma: float, length: int, rms_window: int
) -> pd.Series:
    l0 = _ultimate_smoother(close, length).to_numpy()
    n = len(l0)
    l1 = np.zeros(n)
    for i in range(1, n):
        l1[i] = -gamma * l0[i] + l0[i - 1] + gamma * l1[i - 1]

    diff = pd.Series(l0 - l1, index=close.index)
    rms = np.sqrt((diff ** 2).rolling(rms_window).mean())
    osc = diff / rms.replace(0.0, np.nan)
    return osc.fillna(0.0)


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
    lag_length: int = 30,
    lag_gamma: float = 0.5,
    rms_window: int = 100,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Laguerre Oscillator (unbounded) is rolling z-scored over `zscore_window`
    bars and tanh-squashed to [-1,+1] before use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    osc = _laguerre_oscillator(close, lag_gamma, lag_length, rms_window)

    roll_mean = osc.rolling(zscore_window).mean()
    roll_std = osc.rolling(zscore_window).std()
    zscore = (osc - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    lag_length: int = 30,
    lag_gamma: float = 0.5,
    rms_window: int = 100,
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
        lag_length=lag_length,
        lag_gamma=lag_gamma,
        rms_window=rms_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
