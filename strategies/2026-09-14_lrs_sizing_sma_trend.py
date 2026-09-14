"""Strategy: SMA(trend_window) directional gate with continuous Normalized
Linear Regression Slope (LRS) sizing overlay + deadband, leverage-cap-aware
for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Normalized Linear Regression Slope (LRS): the raw least-squares regression
slope (beta) fit to closing prices over a rolling `lrs_window`-bar lookback,
normalized by current price and expressed as a percentage:
    normalized_slope = (raw_slope / current_price) * 100
This makes the slope comparable across instruments/price levels (a $500
stock and a $5 stock with the same % trend strength get the same reading).
Per https://www.tradingpedia.com (via Google AI-overview synthesis,
browser_exec fallback -- web_search's DDGS backend returned a
non-actionable snippet-only result for the query).

This repo has 1 prior Linear Regression Slope entry (2026-09-10-100, a
short-lookback pullback/reversal binary trigger, source's own disclosed
counter-trend rule: long when slope turns NEGATIVE -- a mean-reversion
framing). This iteration is a distinct construction: uses LRS as a
TREND-FOLLOWING continuous sizing dial (not mean-reversion) -- the raw
normalized slope, rolling z-scored and tanh-squashed to bound it, sized
within an SMA(trend_window) uptrend gate. First continuous-sizing dial /
trend-following framing of LRS in this repo.

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


def _normalized_lrs(close: pd.Series, lrs_window: int) -> pd.Series:
    """Rolling least-squares regression slope of close, normalized by price.

    normalized_slope = (raw_slope / current_price) * 100
    """
    x = np.arange(lrs_window, dtype=float)
    x_mean = x.mean()
    x_demeaned = x - x_mean
    denom = (x_demeaned ** 2).sum()

    def _slope(window: np.ndarray) -> float:
        y_mean = window.mean()
        return float(((x_demeaned) * (window - y_mean)).sum() / denom)

    raw_slope = close.rolling(lrs_window).apply(_slope, raw=True)
    normalized = (raw_slope / close) * 100.0
    return normalized


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
    lrs_window: int = 20,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Normalized LRS is unbounded, so it's rolling-z-scored over
    `zscore_window` bars and tanh-squashed to [-1,+1] before use as a sizing
    dial.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    lrs = _normalized_lrs(close, lrs_window)
    roll_mean = lrs.rolling(zscore_window).mean()
    roll_std = lrs.rolling(zscore_window).std()
    zscore = (lrs - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    lrs_window: int = 20,
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
        lrs_window=lrs_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
