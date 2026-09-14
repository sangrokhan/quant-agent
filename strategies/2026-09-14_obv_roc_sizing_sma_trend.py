"""Strategy: SMA(trend_window) directional gate with continuous On-Balance
Volume (OBV) rate-of-change sizing overlay + deadband, leverage-cap-aware
for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
On-Balance Volume (OBV, Joseph Granville, 1963): cumulative running total of
volume, added on up-close days and subtracted on down-close days --
OBV_t = OBV_{t-1} + sign(Close_t - Close_{t-1}) * Volume_t
This repo has 8+ prior OBV entries (EMA-crossover confirmation filter,
divergence variants, breakout confirmation), all binary trigger/filter
constructions. None used OBV as a continuous sizing dial -- because raw OBV
is a cumulative running total (unbounded, trending with cumulative volume
over the sample), a direct z-score of the level would be nonstationary. This
iteration instead computes OBV's own rolling RATE OF CHANGE (pct_change over
a short window, the same "reframe a cumulative/trending indicator via its
own short-horizon rate of change" technique already validated in this repo
for NVI, 2026-09-14-131), rolling z-scored and tanh-squashed to [-1,+1],
used as a sizing multiplier within an SMA(trend_window) uptrend gate. First
OBV continuous-sizing variant in this repo.

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


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """Cumulative On-Balance Volume."""
    direction = np.sign(close.diff().fillna(0.0))
    signed_volume = direction * volume
    return signed_volume.cumsum()


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
    roc_window: int = 20,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    OBV's own rolling `roc_window`-bar rate of change (a diff, not pct_change,
    since OBV can cross zero) is rolling-z-scored over `zscore_window` bars
    and tanh-squashed to [-1,+1] before use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    trend_long = close > close.rolling(trend_window).mean()
    obv = _obv(close, volume)
    obv_roc = obv.diff(roc_window)
    roll_mean = obv_roc.rolling(zscore_window).mean()
    roll_std = obv_roc.rolling(zscore_window).std()
    zscore = (obv_roc - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    roc_window: int = 20,
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
        roc_window=roc_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
