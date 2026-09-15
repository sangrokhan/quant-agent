"""Strategy: Ehlers Reversion Index (TASC Jan 2026) reframed as a CONTINUOUS
SIZING dial within an SMA(trend_window) uptrend gate, leverage-cap-aware for
crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Direct fix for this same cron trigger's prior rejection 2026-09-16-128
(Ehlers Reversion Index binary crossover-with-time-stop signal: equity QQQ/
SPY Sharpe near-miss ceiling ~0.92-0.98 across a 144-combo parameter search,
crypto BTC/USDT+ETH/USDT decisively rejected on max-drawdown at full binary
exposure). This sub-iteration applies the repo's repeatedly-validated
continuous-sizing-dial pattern instead: the raw Reversion Index (RI) value
-- already naturally bounded [-1, +1] by construction (net price change
over `ri_length` bars normalized by the sum of absolute changes over the
same window), no z-score/tanh needed -- is used DIRECTLY as a sizing
multiplier (rather than only its crossover-vs-Smooth signal), gated by an
SMA(trend_window) uptrend filter (rather than the prior entry's "ranging
regime" proxy, since RI itself already captures the net directional-move
information a Smooth/Trigger crossover was trying to time), with a deadband
to cut turnover and a leverage_cap for crypto from the start (per this
cron trigger's established crypto-retune pattern for pure trend-following/
oscillator signals that need risk control on raw crypto volatility).

Source (unchanged from 2026-09-16-128):
https://www.tradingview.com/script/V35NeC45-TASC-2026-01-The-Reversion-Index/
(PineCodersTASC port of John F. Ehlers, TASC Jan 2026).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _reversion_index(close: pd.Series, length: int) -> pd.Series:
    d = close.diff()
    ds = d.rolling(length).sum()
    ads = d.abs().rolling(length).sum()
    ri = ds / ads.replace(0.0, np.nan)
    return ri.fillna(0.0)


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
    ri_length: int = 20,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    RI (already bounded [-1,+1] by construction) is used directly as the
    sizing dial -- no z-score/tanh transform needed.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    ri = _reversion_index(close, ri_length)

    raw_exposure = base_exposure + sensitivity * ri
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ri_length: int = 20,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        ri_length=ri_length,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
