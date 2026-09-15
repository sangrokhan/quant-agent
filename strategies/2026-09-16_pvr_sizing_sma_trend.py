"""Strategy: SMA(trend_window) directional gate with continuous Price-Volume
Rank (PVR, Anthony J. Macek) sizing overlay + deadband, leverage-cap-aware
for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Price-Volume Rank (PVR), designed by Anthony J. Macek (Stocks &
Commodities V.12:6, 1994), per LazyBear's TradingView port visited this
iteration (https://www.tradingview.com/v/vho8gnBR/): "compares the
direction of the change in price (up or down) to the direction of the
change in volume and assigns a number to that specific relationship... to
determine our position within a typical market cycle." Source's own PVR
levels:
    PVR=1: price UP, volume UP     (most bullish -- healthy uptrend)
    PVR=2: price UP, volume DOWN   (weakening momentum warning)
    PVR=3: price DOWN, volume DOWN (selling pressure abating -- potential
                                     buy opportunity ahead)
    PVR=4: price DOWN, volume UP   (most bearish -- selling pressure at its
                                     greatest)
The source's own "MA Crossover Mode" trades a slow/fast SMA(5/10) of PVR:
buy when the slow MA falls below the fast MA (PVR trending toward more
bullish, i.e. numerically lower), sell when the slow MA crosses back above
the fast MA, with a 2.5 warning/confirmation level. First PVR-specific
strategy in this repo -- distinct from every other volume-flow indicator
already tested (OBV, PVI, NVI, CMF, MFI, A/D Line, etc.), none of which use
this 4-state directional-quadrant construction.

This iteration reframes PVR as a CONTINUOUS SIZING dial: since PVR is
natively bounded [1,4] with LOWER values more bullish, it is inverted and
rescaled to [-1,1] via (2.5-PVR_smoothed)/1.5 (so PVR=1 -> +1 fully bullish,
PVR=4 -> -1 fully bearish, PVR=2.5 -> 0 neutral, matching the source's own
2.5 confirmation level as the dial's zero point), smoothed with the
source's own slow/fast SMA pairing collapsed into a single SMA(pvr_window)
for simplicity, used as an exposure multiplier inside an SMA(trend_window)
uptrend gate with a deadband to cut turnover, following this repo's
established continuous-sizing-dial pattern.

Source: https://www.tradingview.com/v/vho8gnBR/ (visited this iteration,
browser_exec fallback; first search attempt with a wrong author
attribution returned an unrelated engineering-economics textbook, second
search with the correct "metastock formula" framing found the right
Anthony J. Macek attribution).

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


def _pvr_raw(df: pd.DataFrame) -> pd.Series:
    """Raw {1,2,3,4} Price-Volume Rank per Macek's own quadrant definition."""
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(0.0, index=close.index)

    price_up = close.diff() > 0
    volume_up = volume.diff() > 0

    pvr = pd.Series(np.nan, index=close.index)
    pvr = pvr.mask(price_up & volume_up, 1.0)
    pvr = pvr.mask(price_up & ~volume_up, 2.0)
    pvr = pvr.mask(~price_up & ~volume_up, 3.0)
    pvr = pvr.mask(~price_up & volume_up, 4.0)
    return pvr


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
    pvr_window: int = 10,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    PVR (natively bounded [1,4], lower=more bullish) is smoothed over
    `pvr_window` bars and rescaled to [-1,+1] via (2.5-PVR)/1.5 (matching
    the source's own 2.5 confirmation level as the zero point) before use
    as a sizing dial, gated by an SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    pvr_raw = _pvr_raw(df)
    pvr_smoothed = pvr_raw.rolling(pvr_window).mean()
    dial = ((2.5 - pvr_smoothed) / 1.5).clip(lower=-1.0, upper=1.0).fillna(0.0)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    pvr_window: int = 10,
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
        pvr_window=pvr_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
