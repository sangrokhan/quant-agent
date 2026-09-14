"""Strategy: SMA(trend_window) directional gate with continuous Trend
Trigger Factor (TTF, M.H. Pee, TASC Dec 2004) sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Trend Trigger Factor (M.H. Pee, TASC Dec 2004): buy_power = current n-bar
HighestHigh minus prior n-bar LowestLow; sell_power = prior n-bar
HighestHigh minus current n-bar LowestLow; TTF = 100*(buy_power-sell_power)
/(0.5*(buy_power+sell_power)) -- already confirmed in this repo's prior
entry 2026-09-05-015 (which used a binary zero-line-crossing entry/exit
trigger). Re-confirmed via
https://stonehillforex.com/2022/10/trend-trigger-factor-as-a-confirmation-indicator/
(visited this iteration): "this indicator is a below-chart zero-line
cross" confirmation-style oscillator.

This iteration reframes TTF as a CONTINUOUS SIZING dial: TTF is rolling
z-score normalized (unbounded by construction, unlike RAVI/DeMarker), then
scales exposure within an SMA(trend_window) uptrend gate -- reusing this
cron trigger's validated continuous-sizing-dial pattern (22+ prior
indicator families tested this way).

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


def _ttf(high: pd.Series, low: pd.Series, period: int = 8) -> pd.Series:
    """TTF = 100*(buy_power - sell_power) / (0.5*(buy_power + sell_power)).

    buy_power = HighestHigh(current period) - LowestLow(prior period)
    sell_power = HighestHigh(prior period) - LowestLow(current period)
    (M.H. Pee, TASC Dec 2004, difference-based construction as confirmed
    in this repo's prior entry 2026-09-05-015.)
    """
    hh_curr = high.rolling(period).max()
    ll_curr = low.rolling(period).min()
    hh_prior = high.shift(period).rolling(period).max()
    ll_prior = low.shift(period).rolling(period).min()

    buy_power = hh_curr - ll_prior
    sell_power = hh_prior - ll_curr

    denom = (0.5 * (buy_power + sell_power)).replace(0, np.nan)
    return 100.0 * (buy_power - sell_power) / denom


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
    ttf_period: int = 8,
    zscore_window: int = 90,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    ttf = _ttf(high, low, ttf_period)

    ttf_mean = ttf.rolling(zscore_window).mean()
    ttf_std = ttf.rolling(zscore_window).std().replace(0, np.nan)
    ttf_zscore = ((ttf - ttf_mean) / ttf_std).clip(lower=-2.5, upper=2.5)

    raw_exposure = base_exposure + sensitivity * (ttf_zscore / 2.5)
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ttf_period: int = 8,
    zscore_window: int = 90,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        ttf_period=ttf_period,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
