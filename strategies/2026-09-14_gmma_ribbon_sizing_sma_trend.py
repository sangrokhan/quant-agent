"""Strategy: SMA(trend_window) directional gate with continuous Guppy
Multiple Moving Average (GMMA) ribbon-spread sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Guppy Multiple Moving Average (GMMA, Daryl Guppy, late 1990s): two groups of
6 EMAs each -- short-term group EMA(3,5,8,10,12,15) proxying short-term
trader/speculator activity, long-term group EMA(30,35,40,45,50,60) proxying
long-term investor/institutional sentiment. Formula confirmed via Google
AI-overview (browser_exec fallback after web_search's DDGS backend failed
with a TLS/connection error).

This repo has 5+ prior GMMA entries (2026-09-04-062, 2026-09-10-061, and
several no_candidate iterations noting the family as "saturated"), all
binary ribbon-crossover or ribbon-compression triggers, never as a
continuous sizing dial. This iteration reframes GMMA as a CONTINUOUS SIZING
dial: the normalized spread between the short-group EMA average and the
long-group EMA average (as a fraction of price, z-scored over a rolling
window to bound it), used as a sizing multiplier within an SMA(trend_window)
uptrend gate -- following this cron trigger's validated continuous-sizing-
dial pattern for indicator families previously only tested as binary
triggers.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SHORT_GROUP = (3, 5, 8, 10, 12, 15)
LONG_GROUP = (30, 35, 40, 45, 50, 60)


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _gmma_ribbon_spread(close: pd.Series) -> pd.Series:
    """(short-group EMA average - long-group EMA average) / close.

    A raw, unbounded ribbon-spread measure -- z-scored downstream to bound it
    for use as a sizing dial.
    """
    short_avg = sum(close.ewm(span=p, adjust=False).mean() for p in SHORT_GROUP) / len(SHORT_GROUP)
    long_avg = sum(close.ewm(span=p, adjust=False).mean() for p in LONG_GROUP) / len(LONG_GROUP)
    return (short_avg - long_avg) / close


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
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    The raw GMMA ribbon spread ((short_avg-long_avg)/close) is unbounded, so
    it's rolling-z-scored over `zscore_window` bars and squashed with tanh to
    [-1,+1] before being used as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    raw_spread = _gmma_ribbon_spread(close)
    roll_mean = raw_spread.rolling(zscore_window).mean()
    roll_std = raw_spread.rolling(zscore_window).std()
    zscore = (raw_spread - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    zscore_window: int = 100,
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
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
