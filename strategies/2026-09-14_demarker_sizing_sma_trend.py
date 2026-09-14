"""Strategy: SMA(trend_window) directional gate with continuous DeMarker
(Tom DeMark) sizing overlay + deadband, leverage-cap-aware for crypto from
the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
DeMarker (Tom DeMark): DeMax_t = max(high_t - high_{t-1}, 0),
DeMin_t = max(low_{t-1} - low_t, 0); DeM = SMA(DeMax, n) /
(SMA(DeMax, n) + SMA(DeMin, n)), naturally bounded [0, 1] with centerline
0.5. Confirmed via browser_exec read of
https://tradersunion.com/interesting-articles/forex-indicators-for-traders/demarker-indicator/
("Outputs a line that oscillates between 0 and 1... compares the current
high and low prices to those of the previous candle" -- to gauge demand and
price exhaustion).

This repo has 2 prior DeMarker entries (2026-09-04-154 accepted binary
oversold-bounce/overbought-exit crossover with a 200d SMA uptrend gate;
2026-09-10-126 divergence variant), both BINARY entry/exit constructions.
Neither used DeMarker as a CONTINUOUS SIZING dial. This iteration reframes
the already-bounded-[0,1] DeM value directly (no z-score needed, unlike
unbounded oscillators such as KST/Fisher/NVI tested earlier this cron
trigger) as exposure: distance of DeM from its 0.5 centerline scales
position size within an SMA(trend_window) uptrend gate, following this
cron trigger's validated continuous-sizing-dial pattern (18+ other
indicator families tested this way this trigger).

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


def _demarker(high: pd.Series, low: pd.Series, period: int = 14) -> pd.Series:
    """DeMarker oscillator, bounded [0, 1], centerline 0.5."""
    de_max = (high - high.shift(1)).clip(lower=0.0)
    de_min = (low.shift(1) - low).clip(lower=0.0)
    sma_max = de_max.rolling(period).mean()
    sma_min = de_min.rolling(period).mean()
    denom = (sma_max + sma_min).replace(0, np.nan)
    return sma_max / denom


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
    demarker_period: int = 14,
    base_exposure: float = 0.5,
    sensitivity: float = 1.0,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    DeM ranges [0, 1] around a 0.5 centerline: (DeM - 0.5) * 2 rescales to
    [-1, 1] before applying `sensitivity` and `base_exposure`, matching the
    already-bounded-oscillator sizing pattern used for %B/Aroon/CCI/
    Williams %R earlier this cron trigger.
    """
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    dem = _demarker(high, low, demarker_period)
    dem_centered = ((dem - 0.5) * 2.0).clip(lower=-1.0, upper=1.0)

    raw_exposure = base_exposure + sensitivity * dem_centered
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    demarker_period: int = 14,
    base_exposure: float = 0.5,
    sensitivity: float = 1.0,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        demarker_period=demarker_period,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
