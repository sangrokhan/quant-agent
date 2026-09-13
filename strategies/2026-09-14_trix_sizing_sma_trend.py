"""Strategy: SMA(trend_window) directional gate with continuous TRIX
(triple-smoothed EMA rate-of-change) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-114):
TRIX: triple-smoothed EMA (EMA of EMA of EMA, period n) then the 1-period
percentage rate of change of that triple-smoothed value:
TRIX = (EMA3_today - EMA3_yesterday) / EMA3_yesterday * 100. Formula
confirmed via Google AI overview (browser_exec navigation): Investopedia,
TrendSpider, AvaTrade all agree. The triple smoothing filters out short-term
noise more aggressively than a single/double EMA, and the percentage-ROC
construction is scale-invariant across price levels (like PPO).

Repo has 7 prior TRIX entries, all binary crossover/divergence/pullback
ENTRY triggers, all rejected (one had the lowest grid pass_fraction of its
cron trigger, 0.074). None reframed TRIX as a CONTINUOUS SIZING dial.
Following the established "percentage-normalized but volatility-drifting
magnitude -> rolling z-score -> tanh squash" fix pattern (same as
PPO/CFO/EFI this cron trigger), this iteration normalizes TRIX via a
rolling z-score before tanh-squashing to bounded [-1, 1], then uses it as a
CONTINUOUS SIZING dial within an SMA(trend_window) uptrend gate.

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


def _trix_zscore_signal(
    close: pd.Series, trix_span: int = 14, zscore_window: int = 100
) -> pd.Series:
    """tanh(rolling z-score of TRIX), bounded [-1, 1]."""
    ema1 = close.ewm(span=trix_span, adjust=False).mean()
    ema2 = ema1.ewm(span=trix_span, adjust=False).mean()
    ema3 = ema2.ewm(span=trix_span, adjust=False).mean()
    trix = ema3.pct_change() * 100.0

    rolling_mean = trix.rolling(zscore_window).mean()
    rolling_std = trix.rolling(zscore_window).std().replace(0, np.nan)
    zscore = (trix - rolling_mean) / rolling_std

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
    trix_span: int = 14,
    trix_zscore_window: int = 100,
    base_exposure: float = 0.5,
    trix_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.28,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    trix_signal = _trix_zscore_signal(
        close, trix_span=trix_span, zscore_window=trix_zscore_window
    )

    raw_exposure = base_exposure + trix_sensitivity * trix_signal
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    trix_span: int = 14,
    trix_zscore_window: int = 100,
    base_exposure: float = 0.5,
    trix_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.28,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        trix_span=trix_span,
        trix_zscore_window=trix_zscore_window,
        base_exposure=base_exposure,
        trix_sensitivity=trix_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
