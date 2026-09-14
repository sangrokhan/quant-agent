"""Strategy: SMA(trend_window) directional gate with continuous Volume
Weighted Momentum (VWM) sizing overlay + deadband, leverage-cap-aware for
crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Volume Weighted Momentum (VWM): Price Momentum = Close - Close[n periods
ago] (a plain n-period price difference, NOT rate-of-change and NOT a
volume-weighted price average like VWMA), VWM_raw = Price Momentum *
Volume, VWM = SMA(VWM_raw, smooth_period). VWM oscillates around zero:
positive/large VWM means price rose with high volume (momentum with
conviction), negative/large means price fell with high volume. Source:
https://alfatactix.com/academy/indicators/volume-weighted-momentum
(visited this iteration) -- "VWM is calculated by multiplying price
momentum by volume, then smoothing the result with a moving average...
typically using 14 periods for smoothing."

This repo has many prior volume-weighted indicators (VWMA dual-crossover,
VW-MACD x4, PVO, VPCI, Dormeier ADX+TTI+VPCI, VWMA pullback-bounce) but none
use this specific "raw price-difference times volume, then smoothed"
construction -- VWM is distinct because it weights a *momentum* term
(price difference) by volume directly, rather than weighting the price
average itself (VWMA) or building a MACD-style spread of two VWMAs
(VW-MACD). This is the first plain Volume Weighted Momentum entry in this
repo. Already zero-centered by construction, so this iteration follows the
cron trigger's repeatedly-validated continuous-sizing-dial pattern: VWM
rolling z-scored + tanh-squashed to [-1,1], used as a sizing multiplier
within an SMA(trend_window) uptrend gate, deadband to cut turnover,
leverage_cap for crypto.

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


def _vwm(close: pd.Series, volume: pd.Series, mom_period: int, smooth_period: int) -> pd.Series:
    price_momentum = close.diff(mom_period)
    vwm_raw = price_momentum * volume
    vwm = vwm_raw.rolling(smooth_period).mean()
    return vwm


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
    mom_period: int = 10,
    smooth_period: int = 14,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    VWM (already zero-centered by construction) is rolling z-scored over
    `zscore_window` bars and tanh-squashed to [-1,+1] before use as a
    sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)

    trend_long = close > close.rolling(trend_window).mean()
    vwm = _vwm(close, volume, mom_period, smooth_period)

    roll_mean = vwm.rolling(zscore_window).mean()
    roll_std = vwm.rolling(zscore_window).std()
    zscore = (vwm - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    mom_period: int = 10,
    smooth_period: int = 14,
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
        mom_period=mom_period,
        smooth_period=smooth_period,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
