"""Strategy: SMA(trend_window) directional gate with continuous Ehlers
Voss Predictive Filter diff sizing overlay + deadband, leverage-cap-aware
for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
John Ehlers' Voss Predictive Filter (TASC Aug 2019, "A Peek Into the
Future"), per https://www.prorealcode.com/prorealtime-indicators/voss-predictive-filter-vpf/
(formula already fully confirmed and reused verbatim from this repo's
existing accepted strategy
strategies/2026-09-06_ehlers_voss_predictive_filter.py, no fresh web fetch
needed this sub-step): a narrow bandpass filter on price (`Filt`) plus a
recursive negative-group-delay predictor line (`Voss`), designed to lead
Filt at cyclical turning points. This repo's only prior Voss entry
(2026-09-06-120) used the Voss/Filt CROSSOVER as a binary ENTRY trigger:
QQQ's single-config validators passed Sharpe/MDD/TC-survival/walk-forward
but FAILED parameter sensitivity (relative_std 0.748 vs 0.5 threshold,
Sharpe ranging ~0.2 to ~2.9 across the period/max_hold_days grid) --
rejected as a near-miss specifically due to that instability, and crypto
was rejected decisively. This iteration instead reframes the signed diff
(Voss - Filt) as a CONTINUOUS SIZING dial: rolling z-scored and
tanh-squashed to [-1,+1] (unbounded raw diff) within an SMA(trend_window)
uptrend gate -- the same "unbounded diff -> z-score -> tanh" reframing
pattern already used for TCF, Precision Trend, and DSP earlier this same
cron trigger. Economic rationale: a continuous sizing dial, unlike a
binary crossover-threshold entry, should be inherently less sensitive to
the exact parameter values that determine WHEN a discrete cross fires --
directly addressing the specific failure mode (parameter sensitivity)
that sank the binary predecessor. First Voss Predictive Filter
continuous-sizing variant.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _voss_filter(
    close: pd.Series, period: int, predict: int, bandwidth: float
) -> tuple:
    """Compute Ehlers' Voss Predictive Filter (Filt, Voss) per the
    canonical recursive formula (ProRealCode / TASC Aug 2019)."""
    n = len(close)
    c = close.to_numpy(dtype=float)

    order = 3 * predict
    f1 = math.cos(2 * math.pi / period)
    g1 = math.cos(bandwidth * 2 * math.pi / period)
    s1 = 1.0 / g1 - math.sqrt(1.0 / (g1 * g1) - 1.0)

    filt = np.zeros(n)
    voss = np.zeros(n)

    for i in range(n):
        if i <= 5:
            filt[i] = 0.0
            voss[i] = 0.0
            continue
        c_im2 = c[i - 2] if i >= 2 else c[0]
        filt[i] = (
            0.5 * (1 - s1) * (c[i] - c_im2)
            + f1 * (1 + s1) * filt[i - 1]
            - s1 * filt[i - 2]
        )
        sumc = 0.0
        for count in range(order):
            idx = i - (order - count)
            if idx >= 0:
                sumc += ((count + 1) / order) * voss[idx]
        voss[i] = ((3 + order) / 2.0) * filt[i] - sumc

    return pd.Series(filt, index=close.index, name="filt"), pd.Series(
        voss, index=close.index, name="voss"
    )


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
    period: int = 20,
    predict: int = 3,
    bandwidth: float = 0.25,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Signed diff (Voss - Filt) is rolling-z-scored over `zscore_window`
    bars and tanh-squashed to [-1,+1] before use as a sizing dial, within
    an SMA(trend_window) uptrend gate.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    filt, voss = _voss_filter(close, period, predict, bandwidth)
    diff = (voss - filt).fillna(0.0)

    roll_mean = diff.rolling(zscore_window).mean()
    roll_std = diff.rolling(zscore_window).std()
    zscore = (diff - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    period: int = 20,
    predict: int = 3,
    bandwidth: float = 0.25,
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
        period=period,
        predict=predict,
        bandwidth=bandwidth,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
