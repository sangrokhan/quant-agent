"""Strategy: SMA(short trend_window) trend-following gate with continuous
Bollinger %B inverse-mean-reversion sizing overlay + deadband — crypto
leverage-cap-aware rescue variant.

Hypothesis (knowledge_base id TBD, this cron trigger):
Direct fix attempt for prior id 2026-09-13-085 (Bollinger %B continuous
sizing on a shortened SMA(32) trend gate: accepted QQQ+SPY equity, crypto
decisively rejected 0/36 grid cells). Diagnosis this sub-iteration: the
original strategy (strategies/2026-09-13_percent_b_sizing_shorttrend.py) has
NO deadband/rebalance-buffer mechanism at all -- exposure is recomputed and
re-applied every single bar, producing ~1600 trades over the sample on
crypto (vs ~100-250 for this repo's typical deadband-equipped continuous-
sizing dials). This is what fails transaction-cost survival categorically
(net Sharpe goes strongly NEGATIVE, e.g. -0.32, even though gross Sharpe/MDD
both pass comfortably at low leverage_cap). This sub-iteration adds the
standard `_apply_deadband` no-trade-buffer mechanism (identical construction
to every other continuous-sizing-dial strategy in this repo) on top of the
UNCHANGED %B sizing formula and leverage-cap-aware crypto retune, isolating
whether the deadband alone rescues the crypto rejection.

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
    trend_window: int = 32,
    bb_window: int = 20,
    bb_std: float = 2.0,
    base_exposure: float = 0.8,
    pb_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover. Sizing formula
    unchanged from 2026-09-13-085 (equity-only accept)."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    pb = _percent_b(close, bb_window, bb_std)

    raw_exposure = base_exposure - pb_sensitivity * (pb - 0.5)
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap).fillna(0.0)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 32,
    bb_window: int = 20,
    bb_std: float = 2.0,
    base_exposure: float = 0.8,
    pb_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        bb_window=bb_window,
        bb_std=bb_std,
        base_exposure=base_exposure,
        pb_sensitivity=pb_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
