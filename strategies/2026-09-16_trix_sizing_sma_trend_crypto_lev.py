"""Strategy: SMA(trend_window) directional gate with continuous TRIX
(triple-smoothed EMA rate-of-change) sizing overlay + deadband -- CRYPTO
LEVERAGE-CAP RECALIBRATION of 2026-09-14-114.

Hypothesis (knowledge_base id TBD, this cron trigger):
2026-09-14-114 (TRIX rolling-z-score/tanh continuous sizing dial on
SMA(trend_window) trend gate) accepted decisively on equity (QQQ+SPY, all
5 validators, very low param sensitivity) but was rejected on crypto:
BTC/USDT MDD 40.1% against the 25% threshold at leverage_cap=1.0/
sensitivity=0.6/deadband=0.2 (equity-optimized params). This entry
applies this repo's established leverage-cap-aware retune pattern: cut
leverage_cap to 0.3, scale down base_exposure and deadband proportionally
so the dial's shape (z-scored/tanh-squashed TRIX sizing signal) is
preserved but its exposure ceiling is capped tightly enough for crypto's
higher realized vol to keep drawdown under 25% and avoid the whipsaw that
depressed crypto Sharpe at the equity-tuned high-sensitivity/tight-deadband
config. Formula/source unchanged from 2026-09-14-114 (Investopedia/
TrendSpider/AvaTrade via Google AI overview, browser_exec) -- no new
external fetch needed for this crypto-only recalibration sub-step.

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


def _trix_zscore_signal(
    close: pd.Series, trix_span: int = 14, zscore_window: int = 100
) -> pd.Series:
    """tanh(rolling z-score of TRIX), bounded [-1, 1]."""
    ema1 = close.ewm(span=trix_span, adjust=False).mean()
    ema2 = ema1.ewm(span=trix_span, adjust=False).mean()
    ema3 = ema2.ewm(span=trix_span, adjust=False).mean()
    trix = ema3.pct_change() * 100.0

    rolling_mean = trix.rolling(zscore_window).mean()
    rolling_std = trix.rolling(zscore_window).std().replace(0, np.nan)
    zscore = (trix - rolling_mean) / rolling_std

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
    trix_span: int = 14,
    trix_zscore_window: int = 100,
    base_exposure: float = 0.15,
    trix_sensitivity: float = 0.4,
    leverage_cap: float = 0.25,
    deadband: float = 0.10,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    trix_signal = _trix_zscore_signal(
        close, trix_span=trix_span, zscore_window=trix_zscore_window
    )

    raw_exposure = base_exposure + trix_sensitivity * trix_signal * leverage_cap
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    trix_span: int = 14,
    trix_zscore_window: int = 100,
    base_exposure: float = 0.15,
    trix_sensitivity: float = 0.4,
    leverage_cap: float = 0.25,
    deadband: float = 0.10,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        trix_span=trix_span,
        trix_zscore_window=trix_zscore_window,
        base_exposure=base_exposure,
        trix_sensitivity=trix_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
