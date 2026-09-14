"""Strategy: SMA(trend_window) directional gate with continuous Trend
Quality Indicator (TQI, ATR-normalized regression slope x R-squared)
sizing overlay + deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Trend Quality Indicator (TQI), per the TradingView open-source script
description already vetted in this repo's prior accepted binary-crossover
entry (2026-09-08-054 / strategies/2026-09-08_tqi_regression_r2_crossover.py):
raw TQI = (regression_slope(close, reg_window) / ATR(atr_window)) *
R_squared(close, reg_window), explicitly designed to penalize choppy/
non-linear moves by weighting slope with the fit's own goodness-of-fit.
Prior entry used a binary zero-line-crossover trigger on the smoothed
version (accepted QQQ+SPY, rejected crypto). This iteration reframes raw
TQI itself as a CONTINUOUS SIZING dial instead of a discrete crossover
trigger: rolling z-scored + tanh-squashed to [-1,1], used as a sizing
multiplier within an SMA(trend_window) uptrend gate, deadband to cut
turnover, leverage_cap for crypto. First TQI continuous-sizing variant.

Source: reused formula from prior repo research (TradingView open-source
TQI script description, already confirmed in 2026-09-08-054); this
iteration is a technique variant, not a new-formula test.

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


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr


def _slope_and_r2(close: pd.Series, n: int):
    x = np.arange(n, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    def _slope(window: np.ndarray) -> float:
        y_mean = window.mean()
        return ((x - x_mean) * (window - y_mean)).sum() / x_var

    def _r2(window: np.ndarray) -> float:
        y_mean = window.mean()
        slope = ((x - x_mean) * (window - y_mean)).sum() / x_var
        intercept = y_mean - slope * x_mean
        fitted = intercept + slope * x
        ss_res = ((window - fitted) ** 2).sum()
        ss_tot = ((window - y_mean) ** 2).sum()
        if ss_tot <= 0:
            return 0.0
        return 1.0 - ss_res / ss_tot

    slope = close.rolling(n).apply(_slope, raw=True)
    r2 = close.rolling(n).apply(_r2, raw=True)
    return slope, r2


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
    reg_window: int = 20,
    atr_window: int = 14,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Raw TQI (ATR-normalized regression slope x R-squared) is rolling
    z-scored over `zscore_window` bars and tanh-squashed to [-1,+1] before
    use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    slope, r2 = _slope_and_r2(close, reg_window)
    tr = _true_range(df)
    atr = tr.rolling(atr_window).mean()
    raw_tqi = (slope / atr.replace(0.0, np.nan)) * r2

    roll_mean = raw_tqi.rolling(zscore_window).mean()
    roll_std = raw_tqi.rolling(zscore_window).std()
    zscore = (raw_tqi - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    reg_window: int = 20,
    atr_window: int = 14,
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
        reg_window=reg_window,
        atr_window=atr_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
