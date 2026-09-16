"""Strategy: SMA(trend_window) directional gate with continuous Better
Volume (LazyBear/emini-watch/Dutchy) buy/sell pressure sizing overlay +
deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
The "Better Volume" indicator (original idea emini-watch.com, ProRealTime
port by Dutchy, 2009, per
https://www.prorealcode.com/prorealtime-indicators/better-volume/, read via
web_search -> browser_exec this iteration) discloses an exact buy/sell
volume split, distinct from every volume-pressure indicator already tested
in this repo (Chaikin Money Flow / Money Flow Index use
(Close-Low)/(High-Low); Better Volume instead splits by a
(2*Range +/- (Open-Close)) denominator):

    Value1 (est. buy volume)  = Volume * Range / (2*Range + Open - Close)   if Close > Open
                               = Volume * (Range + Close - Open) / (2*Range + Close - Open)  if Close < Open
                               = 0.5 * Volume                                if Close == Open
    Value2 (est. sell volume) = Volume - Value1

This repo has 1 prior "Better Volume" research attempt (2026-09-09-060,
feasibility-blocked -- could not source an exact formula after 5 URLs, gave
up rather than inventing thresholds). This iteration operationalizes the
now-sourced buy/sell split as a CONTINUOUS SIZING dial:

    pressure = (Value1 - Value2) / Volume   (naturally bounded [-1, +1] by
    construction since Value1 + Value2 == Volume)

used directly as an exposure-sizing dial inside an SMA(trend_window) uptrend
gate + deadband, following this cron trigger's validated continuous-sizing-
dial pattern. First Better Volume strategy in this repo -- distinct from
CMF/MFI/OBV/Klinger/Demand Index/VZO since the buy/sell estimation formula
itself (Range-and-Open/Close-relative apportionment) is unique to this
indicator, not a simple close-position-in-range or price-direction-sign
split.

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


def _better_volume_pressure(df: pd.DataFrame, smooth_window: int) -> pd.Series:
    """(Value1 - Value2) / Volume, naturally bounded [-1, 1], then smoothed.

    Value1 = estimated buy volume, Value2 = estimated sell volume, per the
    Better Volume indicator's Range-and-Open/Close-relative apportionment.
    """
    high, low, close, open_, volume = df["high"], df["low"], df["close"], df["open"], df["volume"]
    rng = (high - low).replace(0.0, np.nan)

    denom_up = (2 * rng + open_ - close).replace(0.0, np.nan)
    value1_up = volume * rng / denom_up

    denom_down = (2 * rng + close - open_).replace(0.0, np.nan)
    value1_down = volume * (rng + close - open_) / denom_down

    value1 = pd.Series(np.nan, index=df.index)
    up_mask = close > open_
    down_mask = close < open_
    flat_mask = close == open_
    value1[up_mask] = value1_up[up_mask]
    value1[down_mask] = value1_down[down_mask]
    value1[flat_mask] = 0.5 * volume[flat_mask]

    value2 = volume - value1
    pressure = (value1 - value2) / volume.replace(0.0, np.nan)
    pressure = pressure.clip(-1.0, 1.0).fillna(0.0)

    if smooth_window > 1:
        pressure = pressure.rolling(smooth_window).mean()
    return pressure


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
    bv_smooth_window: int = 5,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Better Volume pressure is already zero-centered and bounded [-1, 1] by
    construction -- no z-scoring/rescaling needed.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    pressure = _better_volume_pressure(df, bv_smooth_window)

    raw_exposure = base_exposure + sensitivity * pressure
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    bv_smooth_window: int = 5,
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
        bv_smooth_window=bv_smooth_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
