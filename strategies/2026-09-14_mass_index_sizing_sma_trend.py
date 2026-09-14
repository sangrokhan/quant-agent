"""Strategy: SMA(trend_window) directional gate with continuous Mass
Index (Donald Dorsey's high-low-range widening/narrowing gauge) sizing
overlay + deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Mass Index (Donald Dorsey), reusing the formula already confirmed in this
repo's 2 prior Mass Index entries (2026-09-04-075, 2026-09-08-038, both
discrete reversal-bulge/RSI-of-Mass-Index triggers, neither accepted):
Mass Index = sum over `sum_window` bars of [EMA(range, ema_window) /
EMA(EMA(range, ema_window), ema_window)], where range = High - Low. This
double-EMA-ratio construction widens above its ~25 baseline when the
high-low range itself is widening relative to its own recent smoothed
history (regardless of price direction) and narrows when range
contracts -- a pure volatility-expansion gauge, not a directional
indicator by itself. This repo has 2 prior Mass Index entries, both
discrete reversal-bulge triggers (neither accepted). This iteration
reframes Mass Index's own deviation from its 25 baseline as a CONTINUOUS
SIZING dial (larger deviation from 25 = market undergoing more range
expansion, used as a volatility-aware conviction scaler within a directional
trend gate rather than a standalone reversal signal): rolling z-scored +
tanh-squashed to [-1,1], used as a sizing multiplier within an
SMA(trend_window) uptrend gate, deadband to cut turnover, leverage_cap for
crypto. First Mass Index continuous-sizing variant.

Source: reused formula from prior repo research (quantifiedstrategies.com
Mass Index formula, already confirmed in 2026-09-08-038); this iteration
is a technique variant, not a re-test of the same rule.

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


def _mass_index(high: pd.Series, low: pd.Series, ema_window: int, sum_window: int) -> pd.Series:
    rng = high - low
    ema1 = rng.ewm(span=ema_window, adjust=False).mean()
    ema2 = ema1.ewm(span=ema_window, adjust=False).mean()
    ratio = ema1 / ema2.replace(0.0, np.nan)
    return ratio.rolling(sum_window).sum()


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
    ema_window: int = 9,
    sum_window: int = 25,
    baseline: float = 25.0,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Mass Index deviation from its `baseline` (default 25, its published
    long-run norm) is rolling-z-scored over `zscore_window` bars and
    tanh-squashed to [-1,+1] before use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    trend_long = close > close.rolling(trend_window).mean()
    mass_idx = _mass_index(high, low, ema_window, sum_window)
    deviation = mass_idx - baseline

    roll_mean = deviation.rolling(zscore_window).mean()
    roll_std = deviation.rolling(zscore_window).std()
    zscore = (deviation - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ema_window: int = 9,
    sum_window: int = 25,
    baseline: float = 25.0,
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
        ema_window=ema_window,
        sum_window=sum_window,
        baseline=baseline,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
