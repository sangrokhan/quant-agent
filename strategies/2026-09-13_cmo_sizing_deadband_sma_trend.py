"""Strategy: SMA200 trend-following gate with continuous CMO sizing overlay
PLUS an exposure-change deadband (no-trade band) to control turnover.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-13-078):
Direct fix for this cron trigger's own 2026-09-13-076 (CMO continuous sizing,
rejected specifically on transaction-cost survival due to high turnover from
CMO's un-smoothed, noisy bar-to-bar fluctuations -- 562/525 trades). Per
threshold-rebalancing / "tolerance band" literature surfaced this iteration
via web_search (tradevae.com, quantroutine.com, nottldr.com, stockalpha.ai):
"a tolerance band is the range around each target weight within which no
action is taken... threshold rebalancing is cost-efficient because you only
trade when drift becomes material" (a 5% band example is standard). This
repo already has one no-trade-band entry (2026-09-07-026, applied to
inverse-vol sizing, rejected on Sharpe/MDD -- NOT a transaction-cost fix
attempt) and one deadband EMA-crossover entry (2026-09-13-040, accepted, but
a binary crossover signal, not a continuous sizing overlay). This iteration
is the FIRST application of a no-trade/tolerance band specifically to fix a
previously-TC-rejected CONTINUOUS SIZING overlay: only update the held
exposure when the newly-computed raw exposure differs from the last held
exposure by more than `deadband` (e.g. 0.05 = 5%), otherwise carry the prior
exposure forward -- directly cutting rebalance frequency while preserving
the same underlying CMO-driven directional logic.

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
    """Only move the held exposure when raw exposure drifts beyond `deadband`
    from the currently-held value; otherwise carry the prior exposure
    forward. This directly reduces rebalance frequency vs. tracking the raw
    (noisy) signal every bar."""
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
    cmo_window: int = 20,
    base_exposure: float = 1.0,
    cmo_sensitivity: float = 0.4,
    leverage_cap: float = 1.0,
    deadband: float = 0.05,
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
    trend_window: int = 200,
    cmo_window: int = 20,
    base_exposure: float = 1.0,
    cmo_sensitivity: float = 0.4,
    leverage_cap: float = 1.0,
    deadband: float = 0.05,
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
