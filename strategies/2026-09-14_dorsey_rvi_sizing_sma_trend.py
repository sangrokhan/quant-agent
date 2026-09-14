"""Strategy: SMA(trend_window) directional gate with continuous Dorsey
Relative Volatility Index (RVI) sizing overlay + deadband, leverage-cap-aware
for crypto from the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Relative Volatility Index (Donald Dorsey): computed exactly like RSI, but
fed the rolling standard deviation of close prices split into "up-day"
and "down-day" stdev buckets rather than raw price changes -- a measure of
*which direction* volatility is concentrated in. RVI = 100 * EMA(up_stdev) /
(EMA(up_stdev) + EMA(down_stdev)), naturally bounded [0,100] by
construction. Per Donald Dorsey's original methodology as captured in this
repo's own prior 2026-09-05-003 entry (https://www.tradingsim.com/blog/relative-volatility-index),
re-confirmed this iteration via browser_exec Google SERP (web_search's DDGS
backend surfaced only tangential Vervoort/CCI content for the query
attempted, not Dorsey RVI specifically).

This repo has 4 prior Dorsey-RVI-family entries (2026-09-05-003 midline
threshold crossover, accepted QQQ+SPY; 2026-09-09-080 SMA-crossover
confirmation filter, accepted; 2026-09-12-151 Dorsey Inertia
linear-regression-smoothed variant, rejected), ALL binary threshold/
crossover/filter rules. This iteration reframes the RAW RVI value as a
CONTINUOUS SIZING dial (rescaled from [0,100] to [-1,+1] around its natural
midline of 50, exactly like this cron trigger's validated PSY/CTI/Kase
pattern for other naturally-bounded oscillators) within the existing
SMA(trend_window) uptrend gate -- first continuous-sizing framing of Dorsey
RVI in this repo.

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


def _relative_volatility_index(
    close: pd.Series, rvi_window: int, rvi_smooth: int
) -> pd.Series:
    stdev = close.rolling(rvi_window, min_periods=max(2, rvi_window // 2)).std()
    up_move = close.diff() > 0
    up_stdev = stdev.where(up_move, 0.0)
    down_stdev = stdev.where(~up_move, 0.0)

    up_ema = up_stdev.ewm(span=rvi_smooth, adjust=False).mean()
    down_ema = down_stdev.ewm(span=rvi_smooth, adjust=False).mean()

    denom = (up_ema + down_ema).replace(0.0, np.nan)
    rvi = 100.0 * up_ema / denom
    return rvi.fillna(50.0)


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
    rvi_window: int = 10,
    rvi_smooth: int = 14,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    RVI is bounded [0,100] by construction; rescaled to [-1,+1] via
    (RVI-50)/50 (centered on Dorsey's own midline), then used directly as a
    sizing dial -- no additional normalization window needed.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    rvi = _relative_volatility_index(close, rvi_window, rvi_smooth)
    rvi_centered = (rvi - 50.0) / 50.0  # rescale [0,100] -> [-1,+1]

    raw_exposure = base_exposure + sensitivity * rvi_centered
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    rvi_window: int = 10,
    rvi_smooth: int = 14,
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
        rvi_window=rvi_window,
        rvi_smooth=rvi_smooth,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
