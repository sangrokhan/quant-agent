"""Strategy: SMA(trend_window) directional gate with continuous Chande
Forecast Oscillator (CFO) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-112):
Chande Forecast Oscillator (Tushar Chande): CFO = (Close - LinRegForecast(n))
/ Close * 100, where LinRegForecast is the n-period least-squares linear
regression forecast value (default n=14). Measures the percentage deviation
of the actual close from its own statistical trend-line forecast. Formula
confirmed via Google AI overview (browser_exec navigation): LuxAlgo,
LightningChart, positioned.app all agree on this construction.

Repo has 2 prior CFO entries (1 rejected zero-line-crossover, 1
no_candidate). Percentage normalization makes CFO comparable across
symbols/price levels (like PPO), but its magnitude still drifts with each
symbol's volatility regime, so (following the established fix pattern) this
iteration normalizes via rolling z-score + tanh squash to bounded [-1, 1],
then uses it as a CONTINUOUS SIZING dial within an SMA(trend_window)
uptrend gate -- distinct from the prior binary zero-line-crossover attempt.

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


def _linreg_forecast(close: pd.Series, window: int) -> pd.Series:
    """n-period rolling least-squares linear regression forecast value
    (the fitted value AT the last bar of each window, i.e. the standard
    "regression forecast" used by CFO/TSF indicators)."""
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    def _fit_last(y: np.ndarray) -> float:
        y_mean = y.mean()
        slope = ((x - x_mean) * (y - y_mean)).sum() / x_var
        intercept = y_mean - slope * x_mean
        return intercept + slope * x[-1]

    return close.rolling(window).apply(_fit_last, raw=True)


def _cfo_zscore_signal(
    close: pd.Series, cfo_window: int = 14, zscore_window: int = 100
) -> pd.Series:
    """tanh(rolling z-score of CFO), bounded [-1, 1]."""
    forecast = _linreg_forecast(close, window=cfo_window)
    cfo = (close - forecast) / close.replace(0, np.nan) * 100.0

    rolling_mean = cfo.rolling(zscore_window).mean()
    rolling_std = cfo.rolling(zscore_window).std().replace(0, np.nan)
    zscore = (cfo - rolling_mean) / rolling_std

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
    cfo_window: int = 14,
    cfo_zscore_window: int = 100,
    base_exposure: float = 0.5,
    cfo_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.28,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    cfo_signal = _cfo_zscore_signal(
        close, cfo_window=cfo_window, zscore_window=cfo_zscore_window
    )

    raw_exposure = base_exposure + cfo_sensitivity * cfo_signal
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    cfo_window: int = 14,
    cfo_zscore_window: int = 100,
    base_exposure: float = 0.5,
    cfo_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.28,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        cfo_window=cfo_window,
        cfo_zscore_window=cfo_zscore_window,
        base_exposure=base_exposure,
        cfo_sensitivity=cfo_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
