"""Strategy: SMA(trend_window) directional gate with continuous
Volume-Weighted MACD (VWMACD) histogram sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Volume-Weighted MACD (VWMACD, Buff Dormeier's amendment to Appel's MACD, per
Optuma/thinkorswim/LuxAlgo): identical MACD construction (fast EMA-style
spread minus slow, with a signal line) but built on Volume-Weighted Moving
Averages (VWMA) instead of plain EMAs, so heavily-traded bars dominate the
momentum read:
    VWMACD_line = VWMA_fast(Close, volume) - VWMA_slow(Close, volume)
    VWMACD_signal = EMA(VWMACD_line, signal_span)
    VWMACD_hist = VWMACD_line - VWMACD_signal
This repo has 4 prior VWMACD entries, all binary signal-line-crossover
triggers (none as a continuous sizing dial). This iteration reframes the
VWMACD histogram (already zero-centered and roughly stationary, similar to
DPO this cron trigger, so no diff/roc needed) as a continuous sizing dial:
rolling z-scored + tanh-squashed to [-1,+1], used as a sizing multiplier
within an SMA(trend_window) uptrend gate, deadband to cut turnover,
leverage_cap for crypto. First VWMACD continuous-sizing variant.

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


def _vwma(close: pd.Series, volume: pd.Series, window: int) -> pd.Series:
    pv = (close * volume).rolling(window).sum()
    vsum = volume.rolling(window).sum()
    return pv / vsum.replace(0.0, np.nan)


def _vwmacd_hist(
    close: pd.Series, volume: pd.Series,
    fast_window: int, slow_window: int, signal_span: int,
) -> pd.Series:
    vwma_fast = _vwma(close, volume, fast_window)
    vwma_slow = _vwma(close, volume, slow_window)
    line = vwma_fast - vwma_slow
    signal = line.ewm(span=signal_span, adjust=False).mean()
    return line - signal


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
    fast_window: int = 12,
    slow_window: int = 26,
    signal_span: int = 9,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    VWMACD histogram (already zero-centered by construction, no diff/roc
    needed) is rolling-z-scored over `zscore_window` bars and tanh-squashed
    to [-1,+1] before use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    trend_long = close > close.rolling(trend_window).mean()
    hist = _vwmacd_hist(close, volume, fast_window, slow_window, signal_span)

    roll_mean = hist.rolling(zscore_window).mean()
    roll_std = hist.rolling(zscore_window).std()
    zscore = (hist - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    fast_window: int = 12,
    slow_window: int = 26,
    signal_span: int = 9,
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
        fast_window=fast_window,
        slow_window=slow_window,
        signal_span=signal_span,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
