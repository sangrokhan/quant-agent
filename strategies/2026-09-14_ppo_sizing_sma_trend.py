"""Strategy: SMA(trend_window) directional gate with continuous Percentage
Price Oscillator (PPO) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-110):
Percentage Price Oscillator: PPO = ((EMA_fast - EMA_slow) / EMA_slow) * 100,
typically fast=12/slow=26 -- a percentage-normalized MACD. Formula confirmed
via Google SERP (browser_exec navigation): StockCharts, Investopedia,
TrendSpider, and Composer/SoFi all agree on this construction.

Repo has 3 prior PPO entries, all binary crossover/histogram-pullback/
zero-line ENTRY triggers, all rejected (two were noted as "near-miss both
symbols"). Unlike raw MACD (absolute price units, scale-dependent across
symbols/price levels), PPO's percentage normalization makes it comparable
across different-priced instruments -- but its MAGNITUDE still drifts with
each symbol's own volatility regime over time, so (following the "unbounded
indicator -> rolling z-score -> tanh squash" fix pattern used for
EFI/RWI-diff/Qstick this cron trigger) this iteration normalizes PPO via a
rolling z-score before tanh-squashing to bounded [-1, 1], then uses it as a
CONTINUOUS SIZING dial within an SMA(trend_window) uptrend gate -- distinct
from all 3 prior binary-trigger PPO attempts.

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


def _ppo_zscore_signal(
    df: pd.DataFrame,
    ppo_fast: int = 12,
    ppo_slow: int = 26,
    zscore_window: int = 100,
) -> pd.Series:
    """tanh(rolling z-score of PPO), bounded [-1, 1]. PPO's percentage
    normalization removes cross-symbol price-level scale dependence, but its
    own magnitude still drifts with volatility regime over time, so a
    rolling z-score is still needed before squashing for sizing use."""
    close = df["close"]
    ema_fast = close.ewm(span=ppo_fast, adjust=False).mean()
    ema_slow = close.ewm(span=ppo_slow, adjust=False).mean()
    ppo = ((ema_fast - ema_slow) / ema_slow.replace(0, np.nan)) * 100.0

    rolling_mean = ppo.rolling(zscore_window).mean()
    rolling_std = ppo.rolling(zscore_window).std().replace(0, np.nan)
    zscore = (ppo - rolling_mean) / rolling_std

    return np.tanh(zscore)


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
    ppo_fast: int = 12,
    ppo_slow: int = 26,
    ppo_zscore_window: int = 100,
    base_exposure: float = 0.5,
    ppo_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.28,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    ppo_signal = _ppo_zscore_signal(
        df, ppo_fast=ppo_fast, ppo_slow=ppo_slow, zscore_window=ppo_zscore_window
    )

    raw_exposure = base_exposure + ppo_sensitivity * ppo_signal
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ppo_fast: int = 12,
    ppo_slow: int = 26,
    ppo_zscore_window: int = 100,
    base_exposure: float = 0.5,
    ppo_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.28,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        ppo_fast=ppo_fast,
        ppo_slow=ppo_slow,
        ppo_zscore_window=ppo_zscore_window,
        base_exposure=base_exposure,
        ppo_sensitivity=ppo_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
