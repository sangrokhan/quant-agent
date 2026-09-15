"""Strategy: SMA(trend_window) directional gate with continuous Percentage
Price Oscillator (PPO) sizing overlay + deadband -- CRYPTO LEVERAGE-CAP
RECALIBRATION of 2026-09-14-110.

Hypothesis (knowledge_base id TBD, this cron trigger):
2026-09-14-110 (PPO rolling-z-score/tanh continuous sizing dial on
SMA(trend_window) trend gate) accepted decisively on equity (QQQ+SPY, all
5 validators, first PPO accept in this repo) but was decisively rejected
on crypto: BTC/USDT MDD 44.5% against the 25% threshold (one of the
larger crypto MDD misses recorded in this repo), with leverage_cap left
at the equity default 1.0. This entry applies this repo's established
leverage-cap-aware retune pattern: cut leverage_cap to 0.25 (slightly
tighter than the repo's usual 0.3 given PPO's larger original MDD miss),
scale down base_exposure and deadband proportionally so the dial's shape
(z-scored/tanh-squashed PPO sizing signal) is preserved but its exposure
ceiling is capped tightly enough for crypto's higher realized vol to keep
drawdown under 25%. Formula/source unchanged from 2026-09-14-110
(StockCharts/Investopedia/TrendSpider/Composer via Google SERP) -- no new
external fetch needed for this crypto-only recalibration sub-step.

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
    """tanh(rolling z-score of PPO), bounded [-1, 1]."""
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
    base_exposure: float = 0.12,
    ppo_sensitivity: float = 0.6,
    leverage_cap: float = 0.25,
    deadband: float = 0.08,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    ppo_signal = _ppo_zscore_signal(
        df, ppo_fast=ppo_fast, ppo_slow=ppo_slow, zscore_window=ppo_zscore_window
    )

    raw_exposure = base_exposure + ppo_sensitivity * ppo_signal * leverage_cap
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
    base_exposure: float = 0.12,
    ppo_sensitivity: float = 0.6,
    leverage_cap: float = 0.25,
    deadband: float = 0.08,
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
