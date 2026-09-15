"""Strategy: SMA(trend_window) directional gate with continuous Relative
Volatility Index (RVI, Dorsey) distance-from-midline sizing overlay +
deadband, leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-15-044, this cron trigger):
Relative Volatility Index (RVI, Donald Dorsey 1993/1995), per TrendSpider's
and StockManiacs' explainers (formula already documented in this repo from
prior iteration 2026-09-05-003, sources not re-fetched this iteration per
the dedupe ledger): an RSI-shaped formula applied to the standard deviation
of close prices (rather than price itself), splitting up-day and down-day
stdev into separate accumulators before computing an RSI-style ratio. This
repo's prior RVI entry (2026-09-05-003) used a discrete midline-crossover
trigger (RVI crosses above 50 = buy, below 40 = close) and was accepted
for equity (QQQ, SPY) but decisively rejected for crypto. This iteration
reuses the identical underlying construction -- a directional-volatility
oscillator -- but as a CONTINUOUS sizing dial rather than a binary
crossover threshold, per this cron trigger's established rescue pattern,
specifically targeting crypto's decisive rejection: RVI's distance from
its own 50 midline is rolling z-scored and tanh-squashed into [-1,+1],
used to scale exposure up/down inside an SMA(trend_window) uptrend gate
with a deadband. Distinct from 2026-09-05-003 (discrete 50/40 threshold
crossover vs continuous midline-distance sizing dial).

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


def _rvi(close: pd.Series, stdev_window: int, smooth_window: int) -> pd.Series:
    """Dorsey's Relative Volatility Index: RSI-shaped formula applied to
    the standard deviation of close prices, split into up-day and
    down-day accumulators.
    """
    stdev = close.rolling(stdev_window).std()
    up_move = close.diff() > 0
    up_stdev = stdev.where(up_move, 0.0)
    down_stdev = stdev.where(~up_move, 0.0)

    avg_up = up_stdev.ewm(span=smooth_window, adjust=False).mean()
    avg_down = down_stdev.ewm(span=smooth_window, adjust=False).mean()

    rs = avg_up / avg_down.replace(0.0, np.nan)
    rvi = 100.0 - (100.0 / (1.0 + rs))
    return rvi


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
    stdev_window: int = 10,
    smooth_window: int = 14,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    RVI's distance from its own 50 midline is rolling z-scored over
    `zscore_window` and tanh-squashed to [-1,+1] before use as a sizing
    dial, gated by an SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    rvi = _rvi(close, stdev_window, smooth_window)
    distance = rvi - 50.0

    roll_mean = distance.rolling(zscore_window).mean()
    roll_std = distance.rolling(zscore_window).std()
    zscore = (distance - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    stdev_window: int = 10,
    smooth_window: int = 14,
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
        stdev_window=stdev_window,
        smooth_window=smooth_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
