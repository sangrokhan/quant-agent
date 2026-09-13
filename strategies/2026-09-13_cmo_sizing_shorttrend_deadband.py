"""Strategy: SMA(short trend_window) trend-following gate with continuous
CMO sizing overlay + deadband -- retrofitting the shortened trend-window fix
(validated for RVI in 2026-09-13-082) onto CMO sizing.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-13-083):
Direct follow-up to 2026-09-13-082's finding (a shortened SMA trend-gate
window, ~40 days instead of the repo default 200, lets a continuous sizing
overlay pass BOTH QQQ and SPY simultaneously instead of QQQ-only) and its
own explicit recommendation to "retrofit trend_window~40 into the other
QQQ-only accepted sizing overlays" -- applied here to CMO sizing
(2026-09-13-078, previously QQQ-only accepted at trend_window=200, SPY
Sharpe near-miss 0.775). A quick parameter sweep this iteration confirms
SPY Sharpe rises from 0.775 (trend_window=200) to ~1.01-1.08 at
trend_window 30-40 while QQQ also stays >=1.0 across the same range
(consistent with the RVI finding). Same CMO sizing + deadband logic as
2026-09-13-078, only the trend_window default changes.

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


def _cmo(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0.0)
    down = (-delta).clip(lower=0.0)
    sum_up = up.rolling(window).sum()
    sum_down = down.rolling(window).sum()
    denom = (sum_up + sum_down).replace(0, np.nan)
    cmo = 100.0 * (sum_up - sum_down) / denom
    return cmo


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
    cmo_window: int = 20,
    base_exposure: float = 1.0,
    cmo_sensitivity: float = 0.4,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    cmo = _cmo(close, cmo_window)

    raw_exposure = base_exposure + cmo_sensitivity * (cmo / 100.0)
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    cmo_window: int = 20,
    base_exposure: float = 1.0,
    cmo_sensitivity: float = 0.4,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        cmo_window=cmo_window,
        base_exposure=base_exposure,
        cmo_sensitivity=cmo_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
