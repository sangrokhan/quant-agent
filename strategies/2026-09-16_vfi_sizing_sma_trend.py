"""Strategy: SMA(trend_window) directional gate with continuous Volume Flow
Indicator (VFI, Markos Katsanos) sizing overlay + deadband, leverage-cap-
aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Volume Flow Indicator (Katsanos, TASC July 2004), per
https://www.quantifiedstrategies.com/volume-flow-indicator/ (visited this
iteration): unlike On-Balance Volume (which signs volume purely on the
close-vs-prior-close direction), VFI compares the change in TYPICAL price
((H+L+C)/3) against a volatility-scaled "cut-off" threshold (a multiple of
the rolling standard deviation of the log change in typical price) before
signing the volume -- price moves too small to clear the cutoff contribute
zero directed volume, filtering out noise. Volume itself is also capped at
a multiple of its own rolling average to exclude outlier spikes. The
cumulative sum of this "directed, capped" volume, divided by the rolling
average volume, is then smoothed to form VFI. Per the source: "When the
indicator rises above the centerline and stays up, the trend is likely
up... The stronger signal is the divergence from price action." This repo
has 1 prior VFI entry (2026-09-12-206, used only as a binary money-flow
GATE for an unrelated growth/value sector-rotation system, decisively
rejected for reasons unrelated to VFI itself). This is the first strategy
to use VFI's own value as the primary signal, reframed as a CONTINUOUS
SIZING dial (rolling z-scored + tanh-squashed to [-1,1], since VFI is not
naturally bounded) inside an SMA(trend_window) uptrend gate with deadband.
First genuine VFI-as-primary-signal strategy in this repo.

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


def _compute_vfi(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    vol_window: int = 130,
    vol_std_window: int = 30,
    cutoff_coef: float = 0.2,
    vol_cap_coef: float = 2.5,
    smooth_span: int = 3,
) -> pd.Series:
    """Volume Flow Indicator (Markos Katsanos), standard published formula:
    typical price TP=(H+L+C)/3; inter = ln(TP) - ln(TP.shift(1)); cutoff =
    cutoff_coef * rolling_std(inter, vol_std_window) * close; vave =
    rolling_mean(volume, vol_window); vmax = vave * vol_cap_coef; vc =
    min(volume, vmax); directed volume = vc if (TP-TP.shift(1))>cutoff,
    -vc if <-cutoff, else 0; VFI = EMA(rolling_sum(directed,vol_window)
    /vave, smooth_span).
    """
    tp = (high + low + close) / 3.0
    inter = np.log(tp) - np.log(tp.shift(1))
    vinter = inter.rolling(vol_std_window).std()
    cutoff = cutoff_coef * vinter * close

    vave = volume.rolling(vol_window, min_periods=max(2, vol_window // 4)).mean()
    vmax = vave * vol_cap_coef
    vc = volume.clip(upper=vmax)

    mf = tp - tp.shift(1)
    directed = pd.Series(0.0, index=close.index)
    directed = directed.where(~(mf > cutoff), vc)
    directed = directed.where(~(mf < -cutoff), -vc)

    raw_vfi = directed.rolling(vol_window, min_periods=max(2, vol_window // 4)).sum() / vave.replace(0.0, np.nan)
    vfi = raw_vfi.ewm(span=smooth_span, adjust=False).mean()
    return vfi.fillna(0.0)


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
    vol_window: int = 130,
    zscore_window: int = 100,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    VFI is not naturally bounded -- rolling z-scored over `zscore_window`
    bars and tanh-squashed to [-1,1] before use as a sizing dial.
    """
    df = _prep(price_df)
    close, high, low, volume = df["close"], df["high"], df["low"], df["volume"]

    trend_long = close > close.rolling(trend_window).mean()
    vfi = _compute_vfi(high, low, close, volume, vol_window=vol_window)

    roll_mean = vfi.rolling(zscore_window).mean()
    roll_std = vfi.rolling(zscore_window).std()
    zscore = (vfi - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    vol_window: int = 130,
    zscore_window: int = 100,
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
        vol_window=vol_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
