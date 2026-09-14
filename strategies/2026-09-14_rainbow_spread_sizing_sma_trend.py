"""Strategy: SMA(trend_window) directional gate with continuous Rainbow
Moving Average fan-out spread sizing overlay + deadband, leverage-cap-aware
for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Rainbow Moving Average (per TradingView/WH SelfInvest/thinkorswim): a
cascade of N SMAs, each smoothing the output of the previous one:
    MA0 = SMA(Close, window)
    MA_k = SMA(MA_{k-1}, window)  for k = 1..num_bands-1
Repo has 12 prior Rainbow entries (cascaded_smoothing/fan_out_spread/
moving_average_stacking family), mostly binary threshold/crossover
triggers off the fan-out spread; one accepted (oscillator_threshold,
per-symbol-tuned binary). None used the fan-out spread as a CONTINUOUS
SIZING dial. This iteration: normalized spread between the fastest (MA0)
and slowest (MA_{num_bands-1}) band, `(MA0 - MA_last) / MA_last`, rolling
z-scored + tanh-squashed to [-1,+1], used as a sizing multiplier within an
SMA(trend_window) uptrend gate. Rationale: a widely fanned-out rainbow
(fast band far above slow band) indicates a mature, strongly-trending move
warranting larger exposure; a tightly bunched rainbow indicates
consolidation/low conviction. First Rainbow continuous-sizing variant.

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


def _rainbow_spread(close: pd.Series, band_window: int, num_bands: int) -> pd.Series:
    """Cascaded SMA-of-SMA fan-out: normalized spread between fastest (MA0)
    and slowest (MA_{num_bands-1}) band."""
    ma = close.rolling(band_window).mean()
    fastest = ma
    for _ in range(num_bands - 1):
        ma = ma.rolling(band_window).mean()
    slowest = ma
    spread = (fastest - slowest) / slowest.replace(0.0, np.nan)
    return spread


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
    band_window: int = 10,
    num_bands: int = 5,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Rainbow fan-out spread is rolling-z-scored over `zscore_window` bars
    and tanh-squashed to [-1,+1] before use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    spread = _rainbow_spread(close, band_window, num_bands)

    roll_mean = spread.rolling(zscore_window).mean()
    roll_std = spread.rolling(zscore_window).std()
    zscore = (spread - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    band_window: int = 10,
    num_bands: int = 5,
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
        band_window=band_window,
        num_bands=num_bands,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
