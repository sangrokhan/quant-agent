"""Strategy: SMA(trend_window) directional gate with continuous Anchored
Momentum sizing overlay + deadband, leverage-cap-aware for crypto from the
start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Anchored Momentum (Rudy Stefenel, TASC 1998): momentum = EMA(ema_period,
close) / SMA(sma_period, close) - 1, a percentage-difference construction
that replaces the noisy two-point momentum calc (price_today -
price_n_days_ago) with a smoother "anchor" (the SMA) while keeping today's
price lag-free via the EMA. Confirmed via
https://doc.stocksharp.com/api-examples/1944_AnchoredMomentum.html
(visited this iteration): "calculates the ratio between EMA and SMA of
candle closing prices... default SmaPeriod=8, EmaPeriod=6." Already
zero-centered by construction (momentum=0 when EMA==SMA). This repo has 1
prior Anchored Momentum entry (2026-09-06-177), a binary
threshold-crossover trigger (accepted QQQ only, SPY/crypto rejected). This
iteration reframes Anchored Momentum's own continuous magnitude as a
CONTINUOUS SIZING dial: rolling z-scored + tanh-squashed to [-1,1], used as
a sizing multiplier within an SMA(trend_window) uptrend gate, deadband to
cut turnover, leverage_cap for crypto. First Anchored Momentum
continuous-sizing variant in this repo.

Source: https://doc.stocksharp.com/api-examples/1944_AnchoredMomentum.html
(visited this iteration, browser_exec fallback -- web_search's DDGS
backend has been unreliable this cron trigger, multiple prior queries
returned no results).

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


def _anchored_momentum(close: pd.Series, ema_period: int, sma_period: int) -> pd.Series:
    ema = close.ewm(span=ema_period, adjust=False).mean()
    sma = close.rolling(sma_period).mean()
    momentum = ema / sma.replace(0.0, np.nan) - 1.0
    return momentum


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
    ema_period: int = 6,
    sma_period: int = 8,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Anchored Momentum (already zero-centered by construction) is rolling
    z-scored over `zscore_window` bars and tanh-squashed to [-1,+1] before
    use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    momentum = _anchored_momentum(close, ema_period, sma_period)

    roll_mean = momentum.rolling(zscore_window).mean()
    roll_std = momentum.rolling(zscore_window).std()
    zscore = (momentum - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ema_period: int = 6,
    sma_period: int = 8,
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
        ema_period=ema_period,
        sma_period=sma_period,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
