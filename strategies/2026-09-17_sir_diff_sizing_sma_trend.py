"""Strategy: Shinohara Intensity Ratio (SIR) -- continuous sizing dial.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-057):
Direct follow-up to 2026-09-17-056 (SIR corrected formula, discrete
StrongRatio-vs-WeakRatio crossover: SPY accepted cleanly, QQQ a
near-miss failing ONLY parameter sensitivity -- Sharpe/MDD passed at
sir_window=14 but degraded sharply for sir_window>=20, relative_std
0.62 > 0.5 threshold). This repo's standard fix for a "discrete-signal
parameter-sensitivity near-miss" is a continuous-sizing-dial transform
(same pattern as e.g. 2026-09-15-024's ASI-diff resolution,
2026-09-14-188's VoRSI-diff resolution): instead of a binary in/out
crossover, use log(StrongRatio/WeakRatio) -- itself already a ratio, so
its log is a natural signed "intensity spread" -- rolling z-scored and
tanh-squashed into a continuous [-1,1] exposure dial, applied inside an
SMA(trend_window) uptrend gate with a deadband to control turnover. The
continuous dial should smooth the sir_window-sensitivity by weighting
partial conviction rather than a hard on/off state, testable on the full
QQQ+SPY+BTC/USDT+ETH/USDT universe (not just QQQ) per repo convention for
sizing-dial variants.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (net exposure, -1..1 or 0..1)
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


def _compute_sir_log_spread(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    prior_close = close.shift(1)

    strong_num = (high - prior_close).clip(lower=0.0)
    strong_den = (prior_close - low).clip(lower=1e-9)
    weak_num = (high - close).clip(lower=0.0)
    weak_den = (close - low).clip(lower=1e-9)

    strong_ratio = strong_num.rolling(window).sum() / strong_den.rolling(window).sum()
    weak_ratio = (weak_num.rolling(window).sum() / weak_den.rolling(window).sum()).clip(lower=1e-9)

    log_spread = np.log(strong_ratio.clip(lower=1e-9) / weak_ratio)
    return log_spread


def generate_signals(
    price_df: pd.DataFrame,
    sir_window: int = 20,
    zscore_window: int = 126,
    trend_window: int = 100,
    deadband: float = 0.1,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous exposure dial in [-leverage_cap, leverage_cap]."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    log_spread = _compute_sir_log_spread(high, low, close, sir_window)

    mean = log_spread.rolling(zscore_window, min_periods=zscore_window // 2).mean()
    std = log_spread.rolling(zscore_window, min_periods=zscore_window // 2).std()
    z = ((log_spread - mean) / std).fillna(0.0)
    dial = np.tanh(z)

    trend_gate = (close > close.rolling(trend_window).mean()).astype(float)

    exposure = dial * trend_gate * leverage_cap
    exposure = exposure.where(exposure.abs() >= deadband, 0.0)
    exposure = exposure.clip(-leverage_cap, leverage_cap)
    exposure = exposure.fillna(0.0)
    return exposure


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Exposure-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = exposure.shift(1).fillna(0) * daily_ret
    return strategy_ret
