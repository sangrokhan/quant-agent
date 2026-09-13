"""Strategy: SMA(trend_window) directional gate with continuous Qstick
sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-108):
Qstick (Tushar Chande): QStick = SMA(n, Close - Open), a candle-body
momentum measure of average net directional movement within the bar.
Formula confirmed via Google SERP (browser_exec fallback after `web_search`
failed with a DDGSException connection error) -- CorporateFinanceInstitute,
QuantifiedStrategies, TradoFunded, and TradingView sources all agree on
QSI = SMA/EMA(n, Close-Open).

Repo has 4 prior Qstick entries, all binary crossover/divergence ENTRY
triggers, all rejected (one full-sample reject noted a stronger low-vol-
regime slice, flagged for a future vol-gated retest). Since raw Qstick =
Close-Open has no fixed scale across symbols/price levels/volatility
regimes (same issue as EFI/RWI-diff), this iteration normalizes it via a
rolling z-score then tanh-squashes to bounded [-1, 1] -- the established
"unbounded indicator -> squash before sizing" fix pattern -- then uses it as
a CONTINUOUS SIZING dial within an SMA(trend_window) uptrend gate, distinct
from all 4 prior binary-trigger attempts.

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


def _qstick_zscore_signal(
    df: pd.DataFrame, qstick_window: int = 14, zscore_window: int = 100
) -> pd.Series:
    """tanh(rolling z-score of SMA-smoothed Qstick), bounded [-1, 1].
    Normalizes for the fact that raw Qstick = SMA(Close-Open) has no fixed
    scale across symbols/price levels."""
    close = df["close"]
    open_ = df["open"]

    raw_qstick = (close - open_).rolling(qstick_window).mean()

    rolling_mean = raw_qstick.rolling(zscore_window).mean()
    rolling_std = raw_qstick.rolling(zscore_window).std().replace(0, np.nan)
    zscore = (raw_qstick - rolling_mean) / rolling_std

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
    qstick_window: int = 14,
    qstick_zscore_window: int = 100,
    base_exposure: float = 0.5,
    qstick_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.28,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    qstick_signal = _qstick_zscore_signal(
        df, qstick_window=qstick_window, zscore_window=qstick_zscore_window
    )

    raw_exposure = base_exposure + qstick_sensitivity * qstick_signal
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    qstick_window: int = 14,
    qstick_zscore_window: int = 100,
    base_exposure: float = 0.5,
    qstick_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.28,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        qstick_window=qstick_window,
        qstick_zscore_window=qstick_zscore_window,
        base_exposure=base_exposure,
        qstick_sensitivity=qstick_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
