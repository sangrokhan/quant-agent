"""Strategy: SMA(trend_window) directional gate with continuous Projection
Oscillator (ProjO, Mel Widner) sizing overlay + deadband, leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-15-035, this cron trigger):
Projection Oscillator (Mel Widner, Ph.D., introduced Technical Analysis of
Stocks & Commodities, July 1995), per
https://www.wisestocktrader.com/indicators/763-projection-oscillator-for-amibroker-afl
(exact AFL source) and https://www.quantifiedstrategies.com/projection-bands/
(qualitative interpretation), both visited this iteration:
  SHIGH(period) = linear-regression slope of High over `period` bars
  SLOW(period)  = linear-regression slope of Low over `period` bars
  UPPBAND[t]    = max over i=0..period-1 of (High[t-i] + i * SHIGH[t])
  LPBAND[t]     = min over i=0..period-1 of (Low[t-i]  + i * SLOW[t])
  ProjO[t]      = 100 * (Close[t] - LPBAND[t]) / (UPPBAND[t] - LPBAND[t])

This is a "slope-adjusted Stochastic": unlike a plain Stochastic (which
just uses the raw high/low range of the lookback window), Projection Bands
project each historical high/low forward by the current linear-regression
slope before taking the max/min, making the oscillator more responsive to
trending moves. Genuinely new indicator family for this repo (0 prior
"Projection Oscillator"/"Projection Bands" entries). Sources' own
interpretation is the standard 80/20 overbought/oversold + crossover +
divergence rules, with an explicit caveat to first qualify trendiness
(e.g. via R-squared/CMO) before trusting strict OB/OS levels in a trending
market.

Rather than a discrete OB/OS threshold rule, this reuses the cron
trigger's established continuous-sizing-dial pattern: ProjO is centered on
its 50 midpoint, rolling z-scored over `zscore_window`, and tanh-squashed
into [-1,+1] as an exposure multiplier inside an SMA(trend_window) uptrend
gate (itself qualifying the "is this a trending market" question the
source raises) with a deadband to cut turnover.

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


def _rolling_slope(series: pd.Series, period: int) -> pd.Series:
    """Linear-regression slope of `series` vs bar index, over a rolling
    window of `period` bars (slope per bar, in `series` units/bar)."""
    x = np.arange(period, dtype=float)
    x_mean = x.mean()
    denom = ((x - x_mean) ** 2).sum()

    def _slope(window: np.ndarray) -> float:
        y_mean = window.mean()
        return float(((x - x_mean) * (window - y_mean)).sum() / denom)

    return series.rolling(period).apply(_slope, raw=True)


def _projection_bands(df: pd.DataFrame, period: int):
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]

    shigh = _rolling_slope(high, period)
    slow = _rolling_slope(low, period)

    # Project each of the last `period` highs/lows forward by i*slope
    # (i=0 is the most recent bar) and take the rolling max/min.
    upp_candidates = []
    low_candidates = []
    for i in range(period):
        upp_candidates.append(high.shift(i) + i * shigh)
        low_candidates.append(low.shift(i) + i * slow)
    upp_band = pd.concat(upp_candidates, axis=1).max(axis=1)
    low_band = pd.concat(low_candidates, axis=1).min(axis=1)
    return upp_band, low_band


def _proj_oscillator(df: pd.DataFrame, period: int) -> pd.Series:
    close = df["close"]
    upp_band, low_band = _projection_bands(df, period)
    band_range = (upp_band - low_band).replace(0.0, np.nan)
    proj_o = 100.0 * (close - low_band) / band_range
    return proj_o


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
    period: int = 14,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    ProjO (the slope-adjusted stochastic, 0-100 scale) is centered on 50,
    rolling z-scored over `zscore_window`, and tanh-squashed to [-1,+1]
    before use as a sizing dial, gated by an SMA(trend_window) uptrend
    filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    proj_o = _proj_oscillator(df, period)

    centered = proj_o - 50.0
    roll_mean = centered.rolling(zscore_window).mean()
    roll_std = centered.rolling(zscore_window).std()
    zscore = (centered - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    period: int = 14,
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
        period=period,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
