"""Strategy: SMA(trend_window) directional gate with continuous Woodie
Pivot Point normalized-distance sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Woodie's Pivot Points, reusing the double-close-weighted formula already
confirmed in this repo's prior accepted entry (2026-09-08-158, a discrete
R1-breakout trigger): PP = (H + L + 2*C) / 4 (prior day's high/low/close,
double-weighted close per Woodie's own construction), R1 = 2*PP - L,
S1 = 2*PP - H. This repo has 5 prior Pivot Point family entries (classic
floor-trader, Camarilla, Woodie), all discrete breakout/bounce triggers off
specific S/R levels, none as a continuous dial. This iteration reframes
today's close position relative to the prior day's pivot, normalized by
the (R1-S1) band width, as a CONTINUOUS SIZING dial: rolling z-scored +
tanh-squashed to [-1,1], used as a sizing multiplier within an
SMA(trend_window) uptrend gate, deadband to cut turnover, leverage_cap for
crypto. First Pivot Point continuous-sizing variant.

Source: reused formula from prior repo research (Swoopr Woodie Pivot
Points article, already confirmed in 2026-09-08-158); this iteration is a
technique variant, not a re-test of the same rule.

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

    Today's close relative to the prior day's Woodie pivot, normalized by
    the (R1-S1) band width, is rolling-z-scored over `zscore_window` bars
    and tanh-squashed to [-1,+1] before use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    trend_long = close > close.rolling(trend_window).mean()

    prior_high = high.shift(1)
    prior_low = low.shift(1)
    prior_close = close.shift(1)
    pivot = (prior_high + prior_low + 2.0 * prior_close) / 4.0
    r1 = 2.0 * pivot - prior_low
    s1 = 2.0 * pivot - prior_high
    band_width = (r1 - s1).replace(0.0, np.nan)

    norm_dist = (close - pivot) / band_width

    roll_mean = norm_dist.rolling(zscore_window).mean()
    roll_std = norm_dist.rolling(zscore_window).std()
    zscore = (norm_dist - roll_mean) / roll_std.replace(0.0, np.nan)
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
