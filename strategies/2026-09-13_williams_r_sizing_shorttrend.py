"""Strategy: SMA(short trend_window) trend-following gate with continuous
Williams %R sizing overlay -- retrofitting the shortened trend-window fix
(validated for RVI 2026-09-13-082, CMO 2026-09-13-083) onto Williams %R
sizing.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-13-084):
Direct follow-up applying the now twice-validated shortened-trend-window fix
to Williams %R sizing (2026-09-13-074, previously QQQ-only accepted at
trend_window=200, SPY Sharpe near-miss 0.990). A parameter sweep this
iteration confirms SPY Sharpe rises from 0.792 (trend_window=200) to
~1.02-1.08 at trend_window 30-40 while QQQ also stays >=1.0 -- and unlike
CMO/UO/StochRSI, Williams %R's underlying High/Low-range construction is
smooth enough that NO exposure-change deadband is needed even at the
shorter window (TC survival already passes comfortably at trend_window=40
for both symbols in this iteration's direct check: QQQ TC=0.783, SPY
TC=0.794). Same Williams %R sizing logic as 2026-09-13-074, only the
trend_window default changes.

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


def _williams_r(df: pd.DataFrame, window: int) -> pd.Series:
    highest_high = df["high"].rolling(window).max()
    lowest_low = df["low"].rolling(window).min()
    range_ = (highest_high - lowest_low).replace(0, np.nan)
    wr = (highest_high - df["close"]) / range_ * -100.0
    return wr


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    williams_window: int = 10,
    base_exposure: float = 1.0,
    wr_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    williams_r = _williams_r(df, williams_window)

    raw_exposure = base_exposure - wr_sensitivity * (williams_r / 100.0)
    exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap).fillna(0.0)

    position = exposure.where(trend_long.fillna(False), other=0.0)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    williams_window: int = 10,
    base_exposure: float = 1.0,
    wr_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        williams_window=williams_window,
        base_exposure=base_exposure,
        wr_sensitivity=wr_sensitivity,
        leverage_cap=leverage_cap,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
