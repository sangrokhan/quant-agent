"""Strategy: SMA(trend_window) directional gate with continuous Kaufman
Efficiency Ratio (ER) sizing overlay + deadband -- CRYPTO LEVERAGE-CAP
RECALIBRATION of 2026-09-14-111.

Hypothesis (knowledge_base id TBD, this cron trigger):
2026-09-14-111 (Kaufman Efficiency Ratio, |NetChange(N)|/Volatility(N),
natively bounded [0,1], as continuous sizing dial on SMA(trend_window)
trend gate) accepted decisively on equity (QQQ+SPY, all 5 validators) but
was decisively rejected on crypto: BTC/USDT MDD 32.9% against the 25%
threshold, 0/108 grid cells passing, at leverage_cap left at the equity
default 1.0. This entry applies this repo's established leverage-cap-aware
retune pattern: cut leverage_cap to 0.3, scale down base_exposure and
deadband proportionally so the dial's shape (ER-based trend-efficiency
sizing signal) is preserved but its exposure ceiling is capped tightly
enough for crypto's higher realized vol to keep drawdown under 25%.
Formula/source unchanged from 2026-09-14-111 (Perry Kaufman, KAMA
component; Google AI overview via browser_exec) -- no new external fetch
needed for this crypto-only recalibration sub-step.

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


def _efficiency_ratio(close: pd.Series, window: int) -> pd.Series:
    """Kaufman Efficiency Ratio: |NetChange(N)| / Volatility(N), bounded
    [0, 1]."""
    net_change = (close - close.shift(window)).abs()
    volatility = close.diff().abs().rolling(window).sum().replace(0, np.nan)
    er = net_change / volatility
    return er.clip(lower=0.0, upper=1.0)


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
    er_window: int = 10,
    base_exposure: float = 0.1,
    er_sensitivity: float = 0.7,
    leverage_cap: float = 0.3,
    deadband: float = 0.08,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover. ER is already
    bounded [0, 1] and unsigned, so exposure = base + sensitivity * ER *
    leverage_cap, clipped, only applied within the SMA uptrend gate."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    er = _efficiency_ratio(close, window=er_window)

    raw_exposure = base_exposure + er_sensitivity * er * leverage_cap
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    er_window: int = 10,
    base_exposure: float = 0.1,
    er_sensitivity: float = 0.7,
    leverage_cap: float = 0.3,
    deadband: float = 0.08,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        er_window=er_window,
        base_exposure=base_exposure,
        er_sensitivity=er_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
