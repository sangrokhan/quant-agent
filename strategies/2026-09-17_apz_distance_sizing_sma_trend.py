"""Strategy: Adaptive Price Zone (APZ, Lee Leibfarth, TASC Sept 2006)
distance-from-basis reframed as a CONTINUOUS SIZING dial within an
SMA(trend_window) uptrend gate, leverage-cap-aware for crypto.

Hypothesis (this cron trigger, iteration 1):
Per Investopedia's disclosed exact formula
(https://www.investopedia.com/articles/trading/10/adaptive-price-zone-indicator-explained.asp,
read this iteration via browser_exec after web_search intermittently
errored/returned no results for several other queries this iteration):

    basis = EMA(EMA(close, 5), 5)                       (double-smoothed EMA)
    volatility_value = EMA(EMA(high - low, 5), 5)        (double-smoothed range)
    upper = basis + dev_factor * volatility_value
    lower = basis - dev_factor * volatility_value

This repo already has two APZ entries (2026-09-07-011: mean-reversion off
the bands, rejected; 2026-09-11-012: ADX-gated ranging-regime breakout,
accepted equity). Neither uses the *basis* series itself as a sizing input
-- both treat APZ purely as a band for discrete entry/exit triggers. This
iteration is a genuinely distinct construction: (close - basis) /
volatility_value, an ATR-analog normalized distance from the fast
double-smoothed EMA centerline, used directly as a CONTINUOUS exposure
dial (rolling z-score + tanh) within an SMA(trend_window) uptrend gate --
following this repo's established "distance-from-adaptive-centerline"
sizing pattern (as used for e.g. Ehlers Instantaneous Trendline, Coral
Trend) but applied to APZ's own volatility-scaled distance measure for the
first time. Economic rationale: when price pushes further above its own
fast-reacting, volatility-scaled centerline within an established uptrend,
that's read as strengthening momentum warranting more exposure; a pullback
toward/through the centerline warrants de-risking, all still gated to zero
whenever the broader trend (SMA(trend_window)) is down.

Source: https://www.investopedia.com/articles/trading/10/adaptive-price-zone-indicator-explained.asp
(read via browser_exec this iteration -- web_search's DDGS backend
intermittently timed out/returned empty for several queries this run,
Google search fallback used for keyword discovery, direct browser page
read used for the exact formula extraction since this backend's
web_extract cannot fetch page content, only search).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns).
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


def _apz_distance(
    high: pd.Series, low: pd.Series, close: pd.Series, ema_period: int,
) -> pd.Series:
    """(close - basis) / volatility_value, per Investopedia's disclosed APZ
    double-smoothed-EMA formula (basis and volatility_value both use two
    cascaded EMAs of the same period)."""
    basis = close.ewm(span=ema_period, adjust=False).mean().ewm(span=ema_period, adjust=False).mean()
    rng = (high - low)
    volatility_value = rng.ewm(span=ema_period, adjust=False).mean().ewm(span=ema_period, adjust=False).mean()
    volatility_value = volatility_value.replace(0.0, np.nan)
    distance = (close - basis) / volatility_value
    return distance


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ema_period: int = 5,
    zscore_window: int = 60,
    sensitivity: float = 0.6,
    base_exposure: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    dial = tanh(rolling z-score of APZ distance-from-basis) -- a higher
    reading (price stretched above its own fast double-smoothed EMA basis,
    relative to its own recent range) pushes exposure up; a lower reading
    pushes exposure down, gated to 0 whenever close is below its
    SMA(trend_window).
    """
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    distance = _apz_distance(high, low, close, ema_period)
    roll_mean = distance.rolling(zscore_window).mean()
    roll_std = distance.rolling(zscore_window).std(ddof=0).replace(0.0, np.nan)
    zscore = (distance - roll_mean) / roll_std
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ema_period: int = 5,
    zscore_window: int = 60,
    sensitivity: float = 0.6,
    base_exposure: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        ema_period=ema_period,
        zscore_window=zscore_window,
        sensitivity=sensitivity,
        base_exposure=base_exposure,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
