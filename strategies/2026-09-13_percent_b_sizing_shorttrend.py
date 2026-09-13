"""Strategy: SMA(short trend_window) trend-following gate with continuous
Bollinger %B inverse-mean-reversion sizing overlay -- SPY-focused
trend-window recalibration retrofit.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-13-085):
Direct follow-up applying the now four-times-validated shortened-trend-
window fix (RVI-082, CMO-083, Williams%R-084 -- all shortened trend_window
from 200 to 30-50 to convert a QQQ-only accept into a dual QQQ+SPY accept)
to Bollinger %B sizing (2026-09-13-071, previously QQQ-only, SPY Sharpe
near-miss 0.979 at trend_window=200). Same %B sizing logic unchanged, only
the SMA trend-confirmation window is swept shorter. Own-data
parameter-recalibration analysis (no new external source this iteration --
continuing the systematic retrofit sweep flagged as a "future idea" in
2026-09-13-082/083/084's notes).

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


def _percent_b(close: pd.Series, bb_window: int, bb_std: float) -> pd.Series:
    mid = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    upper = mid + bb_std * std
    lower = mid - bb_std * std
    band_width = (upper - lower).replace(0, np.nan)
    pb = (close - lower) / band_width
    return pb


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    bb_window: int = 20,
    bb_std: float = 2.0,
    base_exposure: float = 0.8,
    pb_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    pb = _percent_b(close, bb_window, bb_std)

    raw_exposure = base_exposure - pb_sensitivity * (pb - 0.5)
    exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap).fillna(0.0)

    position = exposure.where(trend_long.fillna(False), other=0.0)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
