"""Strategy: SMA(trend_window) directional gate with continuous Gann HiLo
Activator distance sizing overlay + deadband, leverage-cap-aware for
crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Gann HiLo Activator (per LuxAlgo/TradingPedia/Enlightened Stock Trading/
trendsandbreakouts.com): a trailing trend line built from two short-lookback
SMAs, one of the highs (`SMA_high = SMA(High, N)`) and one of the lows
(`SMA_low = SMA(Low, N)`). The line follows SMA_low (as a rising support)
while price is above it in an uptrend state, and flips to follow SMA_high
(as falling resistance) once close crosses below the current line value --
and vice versa. This is a NEW indicator family for this repo (0 prior
entries). This iteration: rather than the standard binary flip-and-hold
trend line, use the raw normalized distance between price and whichever
reference SMA (high or low) is currently "active" per the flip state
machine as a CONTINUOUS SIZING dial -- rolling z-scored + tanh-squashed to
[-1,+1], sized within an SMA(trend_window) uptrend gate. Rationale: how far
price has extended above its active Gann support line is a momentum/
overextension proxy, distinct from a fixed-lag MA distance since the
active reference itself adapts (high vs low SMA) based on trend state.
First Gann HiLo entry of any kind in this repo.

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


def _gann_hilo_line(close: pd.Series, high: pd.Series, low: pd.Series, window: int) -> pd.Series:
    """Gann HiLo Activator trailing line: flips between SMA(High,window)
    and SMA(Low,window) based on close crossing the current line value."""
    sma_high = high.rolling(window).mean()
    sma_low = low.rolling(window).mean()

    n = len(close)
    close_v = close.to_numpy()
    sma_high_v = sma_high.to_numpy()
    sma_low_v = sma_low.to_numpy()
    line = np.full(n, np.nan)

    state = 1  # 1 = following low-average (uptrend support), -1 = following high-average (downtrend resistance)
    for i in range(n):
        if np.isnan(sma_high_v[i]) or np.isnan(sma_low_v[i]):
            continue
        if i == 0 or np.isnan(line[i - 1]):
            line[i] = sma_low_v[i] if state == 1 else sma_high_v[i]
            continue
        prev_line = line[i - 1]
        if state == 1 and close_v[i] < prev_line:
            state = -1
        elif state == -1 and close_v[i] > prev_line:
            state = 1
        line[i] = sma_low_v[i] if state == 1 else sma_high_v[i]

    return pd.Series(line, index=close.index)


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
    gann_window: int = 10,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Normalized distance (Close - GannHiLoLine) / GannHiLoLine is
    rolling-z-scored over `zscore_window` bars and tanh-squashed to
    [-1,+1] before use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    trend_long = close > close.rolling(trend_window).mean()
    line = _gann_hilo_line(close, high, low, gann_window)
    dist = (close - line) / line.replace(0.0, np.nan)

    roll_mean = dist.rolling(zscore_window).mean()
    roll_std = dist.rolling(zscore_window).std()
    zscore = (dist - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    gann_window: int = 10,
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
        gann_window=gann_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
