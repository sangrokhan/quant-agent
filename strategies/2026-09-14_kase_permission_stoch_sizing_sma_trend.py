"""Strategy: SMA(trend_window) directional gate with continuous Kase
Permission Stochastic sizing overlay + deadband, leverage-cap-aware for
crypto from the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Kase Permission Stochastic (Cynthia Kase methodology): a multi-stage
smoothed stochastic. Per the open-source Pine Script v6 at
https://www.tradingview.com/script/xpxIXQLT-Kase-Permission-Stochastic/
(visited this iteration): tripleK = 100*(close - lowest)/(highest - lowest)
over a lookBackPeriod = pstLength*pstX window; tripleDF/tripleDS are
recursively triple-smoothed versions of tripleK (offset by pstX bars,
exponential-style updates); each is further 3-bar SMA'd, then passed
through a custom differential-factor "smooth()" filter (a 5-state IIR
filter using alpha_smooth = 0.45*(length-1)/(0.45*(length-1)+2)) to
produce a Main Line and a Signal Line, both bounded [0, 100]. The source's
own binary rule: buy when Main crosses above Signal, sell on the reverse.

This repo has 2 prior Kase family entries, both Kase PEAK Oscillator
(distinct construction: volatility-normalized directional-move ratio), not
Kase Permission Stochastic. First Kase Permission Stochastic entry in this
repo. This iteration reframes the (Main - Signal) spread as a CONTINUOUS
SIZING dial (rescaled to [-1, 1] by dividing by 100, since each line is
bounded [0,100] making the spread bounded [-100,100]) within an
SMA(trend_window) uptrend gate.

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


def _iir_smooth(price: np.ndarray, length: int) -> np.ndarray:
    """Port of the Pine Script `smooth()` differential-factor filter: a
    5-state IIR smoother with alpha_smooth = 0.45*(length-1)/(0.45*(length-1)+2).
    """
    n = len(price)
    alpha = 0.45 * (length - 1) / (0.45 * (length - 1) + 2)
    s1 = np.zeros(n)
    s2 = np.zeros(n)
    s3 = np.zeros(n)
    s4 = np.zeros(n)
    s5 = np.zeros(n)
    for i in range(n):
        p = price[i]
        prev_s1 = s1[i - 1] if i > 0 else p
        prev_s2 = s2[i - 1] if i > 0 else 0.0
        prev_s4 = s4[i - 1] if i > 0 else 0.0
        prev_s5 = s5[i - 1] if i > 0 else p
        s1[i] = p + alpha * (prev_s1 - p)
        s2[i] = (p - s1[i]) * (1 - alpha) + alpha * prev_s2
        s3[i] = s1[i] + s2[i]
        s4[i] = (s3[i] - prev_s5) * (1 - alpha) ** 2 + alpha ** 2 * prev_s4
        s5[i] = s4[i] + prev_s5
    return s5


def _kase_permission_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    pst_length: int = 9,
    pst_x: int = 5,
    pst_smooth: int = 3,
    smooth_period: int = 10,
) -> tuple[pd.Series, pd.Series]:
    lookback = pst_length * pst_x
    lowest = low.rolling(lookback).min()
    highest = high.rolling(lookback).max()
    rng = (highest - lowest)
    triple_k = np.where(rng > 0, 100.0 * (close - lowest) / rng.replace(0, np.nan), 0.0)
    triple_k = pd.Series(triple_k, index=close.index).fillna(0.0)

    alpha = 2.0 / (1.0 + pst_smooth)
    tk = triple_k.to_numpy()
    n = len(tk)
    triple_df = np.zeros(n)
    triple_ds = np.zeros(n)
    for i in range(n):
        if i == 0:
            triple_df[i] = tk[i]
            triple_ds[i] = tk[i]
            continue
        prev_df_offset = triple_df[i - pst_x] if i - pst_x >= 0 else triple_df[i - 1]
        triple_df[i] = prev_df_offset + alpha * (tk[i] - prev_df_offset)
        prev_ds_offset = triple_ds[i - pst_x] if i - pst_x >= 0 else triple_ds[i - 1]
        triple_ds[i] = (prev_ds_offset * 2 + triple_df[i]) / 3.0

    triple_dfs = pd.Series(triple_df, index=close.index).rolling(3).mean().bfill()
    triple_dss = pd.Series(triple_ds, index=close.index).rolling(3).mean().bfill()

    pst_buffer = pd.Series(_iir_smooth(triple_dfs.to_numpy(), smooth_period), index=close.index)
    pss_buffer = pd.Series(_iir_smooth(triple_dss.to_numpy(), smooth_period), index=close.index)
    return pst_buffer, pss_buffer


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
    pst_length: int = 9,
    pst_x: int = 5,
    pst_smooth: int = 3,
    smooth_period: int = 10,
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
    main_line, signal_line = _kase_permission_stochastic(
        high, low, close, pst_length, pst_x, pst_smooth, smooth_period
    )
    spread = ((main_line - signal_line) / 100.0).clip(lower=-1.0, upper=1.0)

    raw_exposure = base_exposure + sensitivity * spread
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    pst_length: int = 9,
    pst_x: int = 5,
    pst_smooth: int = 3,
    smooth_period: int = 10,
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
        pst_length=pst_length,
        pst_x=pst_x,
        pst_smooth=pst_smooth,
        smooth_period=smooth_period,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
