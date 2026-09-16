"""Strategy: Stiffness Indicator (Markos Katsanos, Nov 2018 Stocks &
Commodities) as a CONTINUOUS SIZING dial within an SMA(trend_window)
uptrend gate, leverage-cap-aware for crypto.

Hypothesis (this cron trigger, iteration 10 of 10):
First Stiffness Indicator strategy in this repo. Per
https://mkatsanos.com/stiffness-indicator (original author's site, read
this iteration), the exact AmiBroker formula:

    MA2 = MA(Close, ma_period) - min_sd * StDev(Close, ma_period)
    CLMA = Close > MA2  (close above a volatility-threshold-adjusted floor)
    PENS = rolling_sum(CLMA, stiffness_period)
    STIFF = PENS * 100 / stiffness_period  (pct of days above threshold)
    STIFFNESS = EMA(STIFF, smooth_coeff)

The indicator counts how often price closed above a volatility-adjusted
moving-average floor over a lookback window -- a naturally bounded [0,100]
measure of trend PERSISTENCE/STRENGTH (not direction), where higher values
(source's own example shades values >75 as "strong trend" periods) signal a
trend that rarely gets violated by pullbacks, implying lower erraticism.
This is a genuinely distinct construction from every prior trend-strength
indicator in this repo (ADX, Choppiness Index, VHF, Chop Zone, Hurst,
Kaufman Efficiency Ratio, etc.) since Stiffness counts discrete threshold-
crossing EVENTS over a rolling window rather than computing a continuous
statistical/geometric measure directly.

This iteration uses the Stiffness value directly (already bounded [0,100],
no z-score needed, following this repo's established "naturally-bounded
oscillator used directly as a sizing dial" pattern, e.g. Williams %R
continuous-range-position, position-in-envelope constructions) as a
continuous exposure multiplier: exposure = base_exposure + sensitivity *
(stiffness/100 - 0.5) * 2, clipped to [0, leverage_cap], applied within an
SMA(trend_window) uptrend gate with a deadband.

Source: https://mkatsanos.com/stiffness-indicator (original author's site,
exact AmiBroker source code, read via browser_exec this iteration --
web_search's DuckDuckGo backend intermittently returning empty for some
queries this run, though a direct query for this indicator succeeded).

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


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def _stiffness(
    close: pd.Series, ma_period: int, min_sd: float, stiffness_period: int, smooth_coeff: int,
) -> pd.Series:
    ma = close.rolling(ma_period).mean()
    std = close.rolling(ma_period).std(ddof=0)
    ma2 = ma - min_sd * std
    clma = (close > ma2).astype(float)
    pens = clma.rolling(stiffness_period).sum()
    stiff = pens * 100.0 / stiffness_period
    stiffness = stiff.ewm(span=smooth_coeff, adjust=False).mean()
    return stiffness


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ma_period: int = 100,
    stiffness_period: int = 60,
    min_sd: float = 0.5,
    smooth_coeff: int = 2,
    sensitivity: float = 0.6,
    base_exposure: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    dial = 2*(stiffness/100 - 0.5), naturally bounded [-1,1] -- a higher
    Stiffness reading (price rarely dipping below its volatility-adjusted
    floor, i.e. a strong/persistent trend) pushes exposure up; a lower
    reading (erratic, frequently-penetrated trend) pushes exposure down,
    gated to 0 whenever close is below its SMA(trend_window).
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    stiffness = _stiffness(close, ma_period, min_sd, stiffness_period, smooth_coeff)
    dial = 2.0 * (stiffness / 100.0 - 0.5)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ma_period: int = 100,
    stiffness_period: int = 60,
    min_sd: float = 0.5,
    smooth_coeff: int = 2,
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
        ma_period=ma_period,
        stiffness_period=stiffness_period,
        min_sd=min_sd,
        smooth_coeff=smooth_coeff,
        sensitivity=sensitivity,
        base_exposure=base_exposure,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
