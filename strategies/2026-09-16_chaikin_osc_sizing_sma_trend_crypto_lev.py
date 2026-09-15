"""Strategy: SMA(trend_window) directional gate with continuous Chaikin
Oscillator (rolling z-score normalized) sizing overlay + deadband --
CRYPTO LEVERAGE-CAP RECALIBRATION of 2026-09-14-122.

Hypothesis (knowledge_base id TBD, this cron trigger):
2026-09-14-122 (Chaikin Oscillator z-score-normalized continuous sizing
dial on SMA(trend_window) trend gate) accepted decisively on equity
(QQQ+SPY, all 5 validators) but was rejected on crypto: BTC/USDT MDD
30.5% against the 25% threshold, with Sharpe already strong (1.515),
TC-survival passing (1.117), and walk-forward passing (1.0) -- an MDD-only
near-decisive miss at leverage_cap left at the equity default 1.0. This
entry applies this repo's established leverage-cap-aware retune pattern:
cut leverage_cap to 0.3, scale down base_exposure and deadband
proportionally so the dial's shape (z-scored Chaikin Oscillator sizing
signal) is preserved but its exposure ceiling is capped tightly enough for
crypto's higher realized vol to keep drawdown under 25%. Formula/source
unchanged from 2026-09-14-122 (Marc Chaikin; investopedia.com/terms/c/
chaikinoscillator.asp, read via browser_exec) -- no new external fetch
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


def _chaikin_oscillator(df: pd.DataFrame, fast: int = 3, slow: int = 10) -> pd.Series:
    """CO = EMA(ADL, fast) - EMA(ADL, slow)."""
    high, low, close, volume = df["high"], df["low"], df["close"], df["volume"]
    range_ = (high - low).replace(0, np.nan)
    mf_multiplier = ((close - low) - (high - close)) / range_
    mf_volume = mf_multiplier.fillna(0.0) * volume
    adl = mf_volume.cumsum()

    co = adl.ewm(span=fast, adjust=False).mean() - adl.ewm(span=slow, adjust=False).mean()
    return co


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
    co_fast: int = 3,
    co_slow: int = 10,
    zscore_window: int = 60,
    base_exposure: float = 0.15,
    sensitivity: float = 0.5,
    leverage_cap: float = 0.3,
    deadband: float = 0.10,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    co = _chaikin_oscillator(df, fast=co_fast, slow=co_slow)
    co_mean = co.rolling(zscore_window).mean()
    co_std = co.rolling(zscore_window).std().replace(0, np.nan)
    co_zscore = ((co - co_mean) / co_std).clip(lower=-2.5, upper=2.5)

    raw_exposure = base_exposure + sensitivity * (co_zscore / 2.5) * leverage_cap
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    co_fast: int = 3,
    co_slow: int = 10,
    zscore_window: int = 60,
    base_exposure: float = 0.15,
    sensitivity: float = 0.5,
    leverage_cap: float = 0.3,
    deadband: float = 0.10,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        co_fast=co_fast,
        co_slow=co_slow,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
