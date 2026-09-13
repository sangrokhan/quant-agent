"""Strategy: SMA(short trend_window) trend-following gate with continuous
Stochastic RSI (StochRSI) sizing overlay + deadband -- SPY-focused
trend-window recalibration retrofit.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-13-088):
Direct follow-up applying the shortened-trend-window fix (RVI-082,
CMO-083, Williams%R-084, %B-085, Aroon-086, UO-087) to StochRSI sizing +
deadband (2026-09-13-080, previously QQQ-only accepted with a narrow TC
margin; SPY was decisively rejected on BOTH Sharpe and TC at
trend_window=200 -- a harder starting point than the other five retrofits,
which were all near-misses on Sharpe alone). Same StochRSI sizing+deadband
logic unchanged; sweeps trend_window (and stochrsi_sensitivity/deadband if
needed, per Aroon-086's lesson that trend_window alone doesn't always
suffice). Own-data parameter-recalibration analysis, no new external source
this iteration.

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


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def _stoch_rsi(close: pd.Series, rsi_window: int, stoch_window: int) -> pd.Series:
    rsi = _rsi(close, rsi_window)
    lowest = rsi.rolling(stoch_window).min()
    highest = rsi.rolling(stoch_window).max()
    denom = (highest - lowest).replace(0, np.nan)
    stoch_rsi = 100.0 * (rsi - lowest) / denom
    return stoch_rsi


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
    rsi_window: int = 14,
    stoch_window: int = 14,
    base_exposure: float = 0.8,
    stochrsi_sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    stoch_rsi = _stoch_rsi(close, rsi_window, stoch_window)

    raw_exposure = base_exposure + stochrsi_sensitivity * ((stoch_rsi - 50.0) / 50.0)
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    rsi_window: int = 14,
    stoch_window: int = 14,
    base_exposure: float = 0.8,
    stochrsi_sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        rsi_window=rsi_window,
        stoch_window=stoch_window,
        base_exposure=base_exposure,
        stochrsi_sensitivity=stochrsi_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
