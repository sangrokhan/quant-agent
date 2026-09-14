"""Strategy: SMA(trend_window) directional gate with continuous Kase Peak
Oscillator (KPO, volatility-normalized max-directional-move) sizing
overlay + deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Kase Peak Oscillator (KPO, Cynthia Kase), reusing the formula already
confirmed in this repo's prior 2 KPO entries (2026-09-08-010,
2026-09-09-057, both binary zero-line/peak-out crossover triggers, neither
accepted): a volatility-normalized ratio of the maximum recent directional
move (over a short_cycle..long_cycle band) to a rolling volatility
normalizer (SMA of stdev of log returns), differencing the "up" leg minus
"down" leg -- already zero-centered by construction, similar to several
other momentum-diff oscillators already reframed as sizing dials this cron
trigger (DPO, VWMACD histogram). This repo has 2 prior KPO entries, both
binary zero-line crossover triggers, neither accepted. This iteration
reframes KPO's own value as a CONTINUOUS SIZING dial: rolling z-scored +
tanh-squashed to [-1,1], used as a sizing multiplier within an
SMA(trend_window) uptrend gate, deadband to cut turnover, leverage_cap for
crypto. First Kase Peak Oscillator continuous-sizing variant.

Source: reused formula from prior repo research (Mladen's MQL4 port on
prorealcode.com forum, already confirmed in 2026-09-09-057); this
iteration is a technique variant, not a re-test of the same rule.

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


def _kpo(
    high: pd.Series, low: pd.Series, close: pd.Series,
    short_cycle: int, long_cycle: int, vol_window: int, vol_sma_window: int,
) -> pd.Series:
    log_ret = np.log(close / close.shift(1))
    vol = log_ret.rolling(vol_window).std()
    vol_norm = vol.rolling(vol_sma_window).mean().replace(0.0, np.nan)

    up_leg = pd.Series(0.0, index=close.index)
    down_leg = pd.Series(0.0, index=close.index)
    for k in range(short_cycle, long_cycle):
        up_move = (np.log(high / high.shift(k))) / np.sqrt(k)
        down_move = (np.log(low.shift(k) / low)) / np.sqrt(k)
        up_leg = np.maximum(up_leg, up_move.fillna(-np.inf))
        down_leg = np.maximum(down_leg, down_move.fillna(-np.inf))

    up_leg = up_leg.replace(-np.inf, 0.0) / vol_norm
    down_leg = down_leg.replace(-np.inf, 0.0) / vol_norm
    kpo = up_leg - down_leg
    return kpo


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
    short_cycle: int = 8,
    long_cycle: int = 30,
    vol_window: int = 9,
    vol_sma_window: int = 30,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    KPO (already zero-centered by construction) is rolling-z-scored over
    `zscore_window` bars and tanh-squashed to [-1,+1] before use as a
    sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    trend_long = close > close.rolling(trend_window).mean()
    kpo = _kpo(high, low, close, short_cycle, long_cycle, vol_window, vol_sma_window)

    roll_mean = kpo.rolling(zscore_window).mean()
    roll_std = kpo.rolling(zscore_window).std()
    zscore = (kpo - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    short_cycle: int = 8,
    long_cycle: int = 30,
    vol_window: int = 9,
    vol_sma_window: int = 30,
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
        short_cycle=short_cycle,
        long_cycle=long_cycle,
        vol_window=vol_window,
        vol_sma_window=vol_sma_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
