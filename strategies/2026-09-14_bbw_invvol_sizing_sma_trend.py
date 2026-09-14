"""Strategy: SMA(trend_window) directional gate with continuous Bollinger
BandWidth INVERSE-VOLATILITY conditioning multiplier + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Bollinger BandWidth (BBW, John Bollinger): BBW = (Upper-Lower)/Middle * 100,
where Upper/Lower/Middle are the standard 20-period/2-std Bollinger Bands --
a pure volatility-compression gauge (distinct from %B, which measures price
POSITION within the bands; BBW measures the bands' WIDTH). Formula confirmed
via Google AI-overview synthesis of ChartSchool/QuestDB (browser_exec).

This repo has 5+ prior Bollinger-squeeze-family entries (TTM Squeeze, BB
Squeeze breakout, Keltner-width squeeze percentile), all using BBW/squeeze
state as a BINARY compression-then-breakout GATE for a separate breakout
trigger. None used BBW directly as an inverse-volatility CONTINUOUS SIZING
multiplier. This iteration follows the GAPO (2026-09-14-137) pattern:
min-max normalize BBW over a rolling window, INVERT it so compression (low
BBW = tight bands = calm/efficient trend) scales exposure UP and expansion
(high BBW = choppy/volatile) scales exposure DOWN, applied within an
SMA(trend_window) uptrend gate. First BBW continuous-sizing / inverse-
volatility-conditioning variant in this repo.

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


def _bollinger_bandwidth(close: pd.Series, bb_window: int, bb_std: float) -> pd.Series:
    """BBW = (Upper - Lower) / Middle * 100."""
    middle = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    upper = middle + bb_std * std
    lower = middle - bb_std * std
    bbw = (upper - lower) / middle.replace(0.0, np.nan) * 100.0
    return bbw


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
    bb_window: int = 20,
    bb_std: float = 2.0,
    norm_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    BBW is rolling min-max normalized to [0,1] over `norm_window` bars, then
    INVERTED (1 - normalized) and rescaled to [-1,+1] so compression scales
    exposure UP.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    bbw = _bollinger_bandwidth(close, bb_window, bb_std)
    roll_min = bbw.rolling(norm_window).min()
    roll_max = bbw.rolling(norm_window).max()
    span = (roll_max - roll_min).replace(0.0, np.nan)
    normalized = (bbw - roll_min) / span
    inverted_centered = (1.0 - normalized.fillna(0.5)) * 2.0 - 1.0  # [0,1] -> invert -> [-1,1]
    dial = inverted_centered.clip(-1.0, 1.0)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    bb_window: int = 20,
    bb_std: float = 2.0,
    norm_window: int = 100,
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
        bb_window=bb_window,
        bb_std=bb_std,
        norm_window=norm_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
