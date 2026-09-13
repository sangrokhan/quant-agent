"""Strategy: SMA200 trend-following gate with continuous Ultimate Oscillator
(UO) sizing overlay PLUS an exposure-change deadband (no-trade band) to
control turnover.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-13-079):
Direct fix for this cron trigger's 2026-09-13-077 (UO continuous sizing,
rejected decisively on transaction-cost survival: net Sharpe went NEGATIVE
after 10bps costs, ~1800 trades on both QQQ/SPY, ~3x the turnover of the
CMO-sizing strategy). Reuses the exposure-change deadband technique that
just fixed the analogous CMO-sizing TC failure this same cron trigger
(2026-09-13-078, deadband=0.10 cut CMO trades 562->56 and flipped net Sharpe
from failing to passing). Per threshold-rebalancing / tolerance-band
literature (tradevae.com, quantroutine.com, nottldr.com, stockalpha.ai, via
web_search): "a tolerance band is the range around each target weight
within which no action is taken". Given UO's turnover was ~3x CMO's, this
iteration widens the deadband grid range upward (up to 0.15-0.20) to test
whether a larger band is needed to bring UO's higher-frequency raw signal
under control.

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


def _ultimate_oscillator(
    df: pd.DataFrame, fast: int = 7, mid: int = 14, slow: int = 28
) -> pd.Series:
    close = df["close"]
    high = df["high"]
    low = df["low"]
    prior_close = close.shift(1)

    bp = close - pd.concat([low, prior_close], axis=1).min(axis=1)
    tr = pd.concat([high, prior_close], axis=1).max(axis=1) - pd.concat(
        [low, prior_close], axis=1
    ).min(axis=1)

    avg_fast = bp.rolling(fast).sum() / tr.rolling(fast).sum().replace(0, np.nan)
    avg_mid = bp.rolling(mid).sum() / tr.rolling(mid).sum().replace(0, np.nan)
    avg_slow = bp.rolling(slow).sum() / tr.rolling(slow).sum().replace(0, np.nan)

    uo = 100.0 * (4 * avg_fast + 2 * avg_mid + avg_slow) / 7.0
    return uo


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
    trend_window: int = 200,
    uo_fast: int = 10,
    uo_mid: int = 14,
    uo_slow: int = 28,
    base_exposure: float = 0.8,
    uo_sensitivity: float = 0.4,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    uo = _ultimate_oscillator(df, fast=uo_fast, mid=uo_mid, slow=uo_slow)

    raw_exposure = base_exposure + uo_sensitivity * ((uo - 50.0) / 50.0)
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    uo_fast: int = 10,
    uo_mid: int = 14,
    uo_slow: int = 28,
    base_exposure: float = 0.8,
    uo_sensitivity: float = 0.4,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        uo_fast=uo_fast,
        uo_mid=uo_mid,
        uo_slow=uo_slow,
        base_exposure=base_exposure,
        uo_sensitivity=uo_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
