"""Strategy: SMA(trend_window) directional gate with continuous Acceleration
Bands (Price Headley) position-in-band sizing overlay + deadband,
leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-16-049, this cron trigger):
Acceleration Bands (Price Headley), per LuxAlgo's library page (the same
source used for this repo's prior discrete breakout attempt, id
2026-09-06-175, decisively rejected): Upper = SMA(High * (1 + 4*(High-Low)
/ (High+Low)), N); Lower = SMA(Low * (1 - 4*(High-Low)/(High+Low)), N);
Midline = SMA(Close, N). Acceleration Bands widen/narrow with the daily
high-low range (a range-derived, not ATR-derived, volatility envelope --
distinct construction from STARC/Keltner which use ATR). The prior discrete
two-consecutive-close breakout entry rule failed decisively (full-sample
Sharpe fail, only a low-vol-slice near-miss artifact). This iteration
reinterprets the same band construction as a continuous sizing dial per
this repo's established position-in-a-channel pattern (STARC %b, Keltner
%b, Bollinger %B), rather than a breakout trigger -- testing whether the
band itself is informative even though the breakout-trigger mechanism
wasn't.

Construction (continuous sizing dial): position of close within the
Acceleration Band channel, pos = (close - midline) / (upper - lower) * 2,
clipped to [-1,+1] (already naturally bounded), used directly as a
continuous sizing dial -- close pinned near the upper band scales exposure
up, near the lower band scales exposure down -- inside an
SMA(trend_window) uptrend gate with a deadband to cut turnover.

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


def _acceleration_bands(
    high: pd.Series, low: pd.Series, close: pd.Series, window: int
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Price Headley's Acceleration Bands.

    Upper = SMA(High * (1 + 4*(High-Low)/(High+Low)), N)
    Lower = SMA(Low * (1 - 4*(High-Low)/(High+Low)), N)
    Midline = SMA(Close, N)
    """
    hl_range = (high - low) / (high + low).replace(0.0, np.nan)
    upper_raw = high * (1.0 + 4.0 * hl_range)
    lower_raw = low * (1.0 - 4.0 * hl_range)
    upper = upper_raw.rolling(window).mean()
    lower = lower_raw.rolling(window).mean()
    midline = close.rolling(window).mean()
    return upper, lower, midline


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
    ab_window: int = 20,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Close's position within the Acceleration Band channel (`ab_window`) is
    clipped to [-1,+1] and used directly as a sizing dial, gated by an
    SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    upper, lower, midline = _acceleration_bands(high, low, close, ab_window)

    band_width = (upper - lower).replace(0.0, np.nan)
    dial = ((close - midline) / band_width * 2.0).clip(lower=-1.0, upper=1.0).fillna(0.0)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ab_window: int = 20,
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
        ab_window=ab_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
