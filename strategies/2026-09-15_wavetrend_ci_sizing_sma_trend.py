"""Strategy: SMA(trend_window) directional gate with continuous WaveTrend
Channel-Index (CI) sizing overlay + deadband, leverage-cap-aware.

Hypothesis (knowledge_base id TBD, this cron trigger):
WaveTrend Oscillator (LazyBear formulation, per
https://pineify.app/resources/blog/wavetrend-oscillator-lazybears-momentum-indicator-guide
visited this iteration):
  AP  = (High + Low + Close) / 3                       (HLC3)
  ESA = EMA(AP, channel_length)
  D   = EMA(|AP - ESA|, channel_length)
  CI  = (AP - ESA) / (0.015 * D)                        (CCI-like normalized channel index)
  WT1 = EMA(CI, average_length)
  WT2 = SMA(WT1, 4)

Prior WaveTrend entries in this repo (2026-09-04-145, 2026-09-08-094,
2026-09-09-055) all used WT1/WT2 signal-line-crossover-in-extreme-zone as a
discrete 0/1 entry/exit gate, and all were rejected for the SAME root
cause: signal too sparse (0-1 trades on equity full-sample, 0/36-0/54 on
crypto) because requiring both an extreme WT2 zone AND a crossover event is
a rare joint condition. None of those three tried WaveTrend as a continuous
sizing dial -- this iteration specifically addresses that prior rejection
reason by reusing the cron trigger's repeatedly-validated continuous-sizing
pattern (rolling z-score + tanh squash of an oscillator, used as an
exposure multiplier inside an SMA trend gate, with deadband to cut
turnover) instead of a discrete threshold/crossover rule. This turns the
same underlying WaveTrend CI signal from a rare discrete event into a
graded, always-available sizing input, which should produce far more
non-empty vol-regime/asset-class grid cells than the prior 3 attempts while
testing the identical indicator construction -- directly probing whether
the earlier rejections were about the underlying signal's information
content (in which case this also fails) or purely about the discrete-event
sparsity of the rule form used (in which case this rescues it, matching the
pattern seen in this cron trigger's several successful "fix" iterations for
other previously-rejected raw-threshold indicators).

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


def _wavetrend_ci(df: pd.DataFrame, channel_length: int, average_length: int):
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]
    ap = (high + low + close) / 3.0
    esa = ap.ewm(span=channel_length, adjust=False).mean()
    d = (ap - esa).abs().ewm(span=channel_length, adjust=False).mean()
    ci = (ap - esa) / (0.015 * d.replace(0.0, np.nan))
    wt1 = ci.ewm(span=average_length, adjust=False).mean()
    wt2 = wt1.rolling(4).mean()
    return ci, wt1, wt2


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
    channel_length: int = 10,
    average_length: int = 21,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    WT1 (the smoothed WaveTrend channel index) is rolling z-scored over
    `zscore_window` bars and tanh-squashed to [-1,+1] before use as a
    sizing dial, gated by an SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    _, wt1, _ = _wavetrend_ci(df, channel_length, average_length)

    roll_mean = wt1.rolling(zscore_window).mean()
    roll_std = wt1.rolling(zscore_window).std()
    zscore = (wt1 - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    channel_length: int = 10,
    average_length: int = 21,
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
        channel_length=channel_length,
        average_length=average_length,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
