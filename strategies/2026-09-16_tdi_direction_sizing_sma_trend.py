"""Strategy: SMA(trend_window) directional gate with continuous Trend
Detection Index (M.H. Pee) Direction-Indicator sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Direct fix attempt for prior id 2026-09-16-110 (Trend Detection Index (TDI,
M.H. Pee): binary long entry when TDI>0 AND Direction Indicator>0, decisively
rejected across all symbols -- QQQ Sharpe 0.034, SPY near-miss 0.935, crypto
2/108 grid passes. Notes: "unnormalized rolling-sum momentum construction (no
volatility scaling) produces noisy/erratic sign flips insufficient for a
robust standalone signal" and "no combo clears both equity symbols even in
best-case per-regime view"). Per
https://www.linnsoft.com/techind/trend-detection-index-tdi (M.H. Pee,
S&C V.19:10, already in this repo's ledger; formula re-used unchanged).

This sub-iteration applies this cron trigger's established fix pattern for
"noisy unnormalized rolling-sum" indicators: instead of a binary AND-gated
threshold trigger on TWO separate raw (unnormalized) sums (TDI and Direction
Indicator), this drops TDI's regime-classification role entirely and uses
ONLY the Direction Indicator (mom_sum = rolling sum of momentum, already the
"cleaner" directional-magnitude half of the pair) as a CONTINUOUS SIZING
dial: rolling-z-scored + tanh-squashed to [-1,1], used directly as an
exposure dial inside an SMA(trend_window) uptrend gate with a deadband. This
isolates whether TDI's own regime-classification logic was adding noise
rather than value, and whether normalizing the Direction Indicator's raw
scale (via z-score) fixes the "noisy sign flips" problem the prior entry's
notes diagnosed. First TDI (Pee)-Direction-Indicator-as-continuous-sizing-
dial strategy in this repo.

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


def _direction_indicator(close: pd.Series, momentum_period: int, sum_period: int) -> pd.Series:
    """Raw Direction Indicator (M.H. Pee): rolling sum of n-day momentum.
    Unchanged formula from strategies/2026-09-15_trend_detection_index_pee.py."""
    mom = close.diff(momentum_period)
    return mom.rolling(sum_period).sum()


def _zscore_tanh(raw: pd.Series, zscore_window: int) -> pd.Series:
    roll_mean = raw.rolling(zscore_window).mean()
    roll_std = raw.rolling(zscore_window).std().replace(0, np.nan)
    zscore = (raw - roll_mean) / roll_std
    return np.tanh(zscore.fillna(0.0))


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
    momentum_period: int = 20,
    sum_period: int = 20,
    zscore_window: int = 100,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    exposure = clip(base_exposure + sensitivity*dial, 0, cap), gated to 0
    whenever close is below its SMA(trend_window).
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    raw_di = _direction_indicator(close, momentum_period=momentum_period, sum_period=sum_period)
    dial = _zscore_tanh(raw_di, zscore_window=zscore_window)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    momentum_period: int = 20,
    sum_period: int = 20,
    zscore_window: int = 100,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        momentum_period=momentum_period,
        sum_period=sum_period,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
