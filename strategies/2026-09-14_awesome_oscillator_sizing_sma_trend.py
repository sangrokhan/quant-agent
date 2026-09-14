"""Strategy: SMA(trend_window) directional gate with continuous Awesome
Oscillator (Bill Williams, dual-SMA median-price momentum) sizing overlay +
deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Awesome Oscillator (AO, Bill Williams): AO = SMA(median_price, fast_window)
- SMA(median_price, slow_window), where median_price = (High+Low)/2 and
canonical windows are fast=5/slow=34 -- already zero-centered by
construction. Formula confirmed via repo's own prior entries
(2026-09-04_awesome_oscillator_zeroline.py, ao_saucer/ao_twin_peaks
variants). This repo has 6+ prior Awesome Oscillator entries (zero-line
crossover, saucer pattern, twin-peaks pattern, alligator-combo), ALL using
AO as a BINARY pattern/crossover ENTRY trigger. None used AO's own
continuous magnitude as a SIZING dial. This iteration follows this cron
trigger's repeatedly-validated continuous-sizing-dial pattern: AO rolling
z-scored + tanh-squashed to [-1,1], used as a sizing multiplier within an
SMA(trend_window) uptrend gate, deadband to cut turnover, leverage_cap for
crypto. First Awesome Oscillator continuous-sizing variant in this repo.

Source: repo's own prior confirmed formula (2026-09-04_awesome_oscillator
family); no new external source needed this iteration -- pure technique
variant on an already-confirmed, canonical formula (Bill Williams' Trading
Chaos, 1995).

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


def _awesome_oscillator(high: pd.Series, low: pd.Series, fast_window: int, slow_window: int) -> pd.Series:
    median_price = (high + low) / 2.0
    ao = median_price.rolling(fast_window).mean() - median_price.rolling(slow_window).mean()
    return ao


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
    fast_window: int = 5,
    slow_window: int = 34,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Awesome Oscillator (already zero-centered by construction) is rolling
    z-scored over `zscore_window` bars and tanh-squashed to [-1,+1] before
    use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    trend_long = close > close.rolling(trend_window).mean()
    ao = _awesome_oscillator(high, low, fast_window, slow_window)

    roll_mean = ao.rolling(zscore_window).mean()
    roll_std = ao.rolling(zscore_window).std()
    zscore = (ao - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    fast_window: int = 5,
    slow_window: int = 34,
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
        fast_window=fast_window,
        slow_window=slow_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
