"""Strategy: SMA(trend_window) directional gate with continuous Fractal
Chaos Bands (FCB) normalized-distance sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Fractal Chaos Bands (Edward William Dreiss; per
https://help.ctrader.com/indicators/built-in/volatility/fractal-chaos-bands/
and https://www.quantifiedstrategies.com/fractal-chaos-bands/, both visited
this iteration): classic 5-bar Williams fractal envelope -- a high fractal
at bar i is confirmed when high[i] is the max of a centered 5-bar window
(high[i-2..i+2]); a low fractal at bar i is confirmed when low[i] is the
min of the same window. The upper band holds the most recent confirmed
high-fractal value (else previous value); the lower band holds the most
recent confirmed low-fractal value. Bands step (stairs) in the direction
of the trend and stay flat/close together in consolidation -- confirmed
consistent with the repo's existing FCB breakout entry
(2026-09-06-145: 5-bar William-fractal envelope, upper=highest high of
most recent confirmed up-fractal / lower=lowest low of most recent
confirmed down-fractal), which is the only prior FCB entry in this repo
(binary breakout trigger). This iteration reframes FCB's own
normalized-distance of Close within its [lower, upper] band -- (Close -
mid) / (upper - lower) where mid = (upper + lower) / 2 -- as a CONTINUOUS
SIZING dial: rolling z-scored + tanh-squashed to [-1,1], used as a sizing
multiplier within an SMA(trend_window) uptrend gate, deadband to cut
turnover, leverage_cap for crypto. First FCB continuous-sizing variant in
this repo.

Source: https://help.ctrader.com/indicators/built-in/volatility/fractal-chaos-bands/
and https://www.quantifiedstrategies.com/fractal-chaos-bands/ (both
visited this iteration via browser_exec -- web_search's DDGS backend
repeatedly returned "No results found" for multiple queries this
iteration, standard browser fallback used throughout).

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


def _fractal_bands(high: pd.Series, low: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Classic 5-bar centered William fractal envelope (fractal_span fixed
    at 5, i.e. 2 bars on each side of the candidate fractal bar) -- confirms
    with a 2-bar lag (fractal at i needs i+2 to have printed)."""
    n = len(high)
    high_vals = high.to_numpy()
    low_vals = low.to_numpy()
    upper = np.full(n, np.nan)
    lower = np.full(n, np.nan)
    last_upper = np.nan
    last_lower = np.nan
    for i in range(n):
        # a candidate fractal at index i-2 confirms once i has printed (window i-4..i)
        j = i - 2
        if j >= 2 and j + 2 < n and j + 2 <= i:
            window_high = high_vals[j - 2 : j + 3]
            window_low = low_vals[j - 2 : j + 3]
            if len(window_high) == 5 and high_vals[j] == np.nanmax(window_high):
                last_upper = high_vals[j]
            if len(window_low) == 5 and low_vals[j] == np.nanmin(window_low):
                last_lower = low_vals[j]
        upper[i] = last_upper
        lower[i] = last_lower
    return pd.Series(upper, index=high.index), pd.Series(lower, index=high.index)


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
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    FCB's normalized position of Close within the [lower, upper] fractal
    band -- (Close - mid) / (upper - lower) -- is rolling-z-scored over
    `zscore_window` bars and tanh-squashed to [-1,+1] before use as a
    sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    trend_long = close > close.rolling(trend_window).mean()
    upper, lower = _fractal_bands(high, low)

    band_width = (upper - lower).replace(0.0, np.nan)
    mid = (upper + lower) / 2.0
    norm_dist = (close - mid) / band_width

    roll_mean = norm_dist.rolling(zscore_window).mean()
    roll_std = norm_dist.rolling(zscore_window).std()
    zscore = (norm_dist - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
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
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
