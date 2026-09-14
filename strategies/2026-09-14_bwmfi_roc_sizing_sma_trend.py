"""Strategy: SMA(trend_window) directional gate with continuous Market
Facilitation Index (BW-MFI, Bill Williams) sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Market Facilitation Index (BW-MFI, Bill Williams), reusing the formula
already confirmed in this repo's 1 prior MFI entry (2026-09-08-095, a
rejected discrete "Squat bar breakout" pattern trigger): MFI = (High -
Low) / Volume, a measure of how much price movement is generated per unit
of volume ("how easily price moves"). Rising MFI = price moving
efficiently with less volume required (trending/efficient market); falling
MFI = more volume required per unit of price movement (choppy/absorption).
This repo has 1 prior MFI entry, a discrete 4-quadrant pattern trigger,
not accepted. This iteration reframes MFI's own rate-of-change (not the
level itself, since raw MFI has no natural centerline) as a CONTINUOUS
SIZING dial: rolling z-scored + tanh-squashed to [-1,1], used as a sizing
multiplier within an SMA(trend_window) uptrend gate, deadband to cut
turnover, leverage_cap for crypto. First BW-MFI continuous-sizing variant.

Source: reused formula from prior repo research (forex-indicators.net
Bill Williams MFI 4-quadrant description, already confirmed in
2026-09-08-095); this iteration is a technique variant, not a re-test of
the same rule.

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
    roc_window: int = 5,
    smooth_window: int = 5,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    BW-MFI = (High - Low) / Volume, smoothed by `smooth_window` SMA, then
    its `roc_window`-bar rate of change (rising MFI = price moving
    increasingly efficiently) is rolling-z-scored over `zscore_window`
    bars and tanh-squashed to [-1,+1] before use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)

    trend_long = close > close.rolling(trend_window).mean()
    mfi_raw = (high - low) / volume.replace(0.0, np.nan)
    mfi_smooth = mfi_raw.rolling(smooth_window).mean()
    mfi_roc = mfi_smooth.pct_change(roc_window)

    roll_mean = mfi_roc.rolling(zscore_window).mean()
    roll_std = mfi_roc.rolling(zscore_window).std()
    zscore = (mfi_roc - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    roc_window: int = 5,
    smooth_window: int = 5,
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
        roc_window=roc_window,
        smooth_window=smooth_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
