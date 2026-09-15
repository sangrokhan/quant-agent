"""Strategy: SMA(trend_window) directional gate with continuous PMO
(DecisionPoint Price Momentum Oscillator, Carl Swenlin) distance-from-signal
sizing overlay + deadband, leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-15-045, this cron trigger):
DecisionPoint Price Momentum Oscillator (PMO, Carl Swenlin), formula
already documented in this repo from prior iteration 2026-09-05-010
(sources not re-fetched this iteration per the dedupe ledger, formula
re-confirmed via this cron trigger's search of stockmaniacs.net/
chartschool.stockcharts.com): a double-smoothed 1-period ROC oscillator --
daily pct-change*10 custom-EMA-smoothed (smoothing factor 2/length, not
the standard 2/(length+1)) over a 35-period window (PMO Line), then again
over a 20-period window; a 10-period EMA of the PMO Line forms the Signal
Line. This repo's prior PMO entry (2026-09-05-010) used a discrete
PMO-crosses-Signal-Line trigger and was decisively rejected across all
asset classes. This iteration reuses the identical double-smoothed-ROC
construction as a CONTINUOUS sizing dial rather than a binary crossover,
per this cron trigger's established rescue pattern: the PMO-minus-Signal
spread is rolling z-scored and tanh-squashed into [-1,+1], used to scale
exposure up/down inside an SMA(trend_window) uptrend gate with a deadband.
Distinct from 2026-09-05-010 (discrete crossover vs continuous spread
sizing dial).

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


def _custom_ema(series: pd.Series, length: int) -> pd.Series:
    """PMO's non-standard EMA smoothing factor: 2/length (not 2/(length+1))."""
    alpha = 2.0 / length
    return series.ewm(alpha=alpha, adjust=False).mean()


def _pmo(close: pd.Series, roc_smooth1: int, roc_smooth2: int, signal_window: int):
    pct_change = close.pct_change().fillna(0.0) * 10.0
    smoothed1 = _custom_ema(pct_change, roc_smooth1)
    pmo_line = _custom_ema(smoothed1, roc_smooth2) * 10.0
    signal_line = pmo_line.ewm(span=signal_window, adjust=False).mean()
    return pmo_line, signal_line


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
    roc_smooth1: int = 35,
    roc_smooth2: int = 20,
    signal_window: int = 10,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    PMO minus its Signal Line is rolling z-scored over `zscore_window` and
    tanh-squashed to [-1,+1] before use as a sizing dial, gated by an
    SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    pmo_line, signal_line = _pmo(close, roc_smooth1, roc_smooth2, signal_window)
    spread = pmo_line - signal_line

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
    roc_smooth1: int = 35,
    roc_smooth2: int = 20,
    signal_window: int = 10,
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
        roc_smooth1=roc_smooth1,
        roc_smooth2=roc_smooth2,
        signal_window=signal_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
