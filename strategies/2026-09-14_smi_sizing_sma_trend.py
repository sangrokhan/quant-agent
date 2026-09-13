"""Strategy: SMA(trend_window) directional gate with continuous Stochastic
Momentum Index (SMI) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-098):
Stochastic Momentum Index (William Blau, 1993; formula per DuckDuckGo HTML
SERP results from luxalgo.com/library/concept/stochastic-momentum-index,
tradiecapital.com, forexmt4indicators.com, ta-lib.org -- all consistent):
unlike Lane's classic %K stochastic (close vs the low of the range), SMI
measures the close's displacement from the MIDPOINT of the recent high-low
range, then double-smooths the numerator (displacement) and denominator
(half-range) SEPARATELY with two chained EMAs before dividing and scaling,
giving a bounded oscillator roughly in [-100, +100]:
    center = (highest_high + lowest_low) / 2
    half_range = (highest_high - lowest_low) / 2
    diff = close - center
    smi = 100 * EMA(EMA(diff, slow), fast) / EMA(EMA(half_range, slow), fast)

This repo has one prior SMI entry (2026-09-04-140), a binary
oversold-threshold signal-line-crossover ENTRY trigger, decisively rejected.
This iteration instead uses SMI as a CONTINUOUS SIZING dial within an
SMA(trend_window) uptrend gate -- same reframing pattern that rescued
VZO/ADX/DMI-diff/CHOP/Vortex-diff-ratio/TSI (and partially RMI) earlier this
cron trigger, all previously rejected as binary triggers, all subsequently
accepted (at least on QQQ) once reframed as continuous position-sizing
dials rather than discrete entry/exit signals.

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


def _smi(df: pd.DataFrame, range_window: int = 13, fast: int = 2, slow: int = 25) -> pd.Series:
    """SMI = 100 * EMA(EMA(diff, slow), fast) / EMA(EMA(half_range, slow), fast),
    bounded roughly [-100, 100]. Uses Blau's common defaults (13-period range
    lookback, 25-then-2 double smoothing)."""
    high = df["high"]
    low = df["low"]
    close = df["close"]

    hh = high.rolling(range_window).max()
    ll = low.rolling(range_window).min()
    center = (hh + ll) / 2.0
    half_range = (hh - ll) / 2.0

    diff = close - center

    diff_s1 = diff.ewm(span=slow, adjust=False).mean()
    diff_s2 = diff_s1.ewm(span=fast, adjust=False).mean()

    hr_s1 = half_range.ewm(span=slow, adjust=False).mean()
    hr_s2 = hr_s1.ewm(span=fast, adjust=False).mean()

    denom = hr_s2.replace(0, np.nan)
    smi = 100.0 * diff_s2 / denom
    return smi.clip(lower=-100.0, upper=100.0)


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
    smi_range_window: int = 13,
    smi_fast: int = 2,
    smi_slow: int = 25,
    base_exposure: float = 0.5,
    smi_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    smi = _smi(df, range_window=smi_range_window, fast=smi_fast, slow=smi_slow)
    smi_norm = smi / 100.0  # rescale to roughly [-1, 1]

    raw_exposure = base_exposure + smi_sensitivity * smi_norm
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    smi_range_window: int = 13,
    smi_fast: int = 2,
    smi_slow: int = 25,
    base_exposure: float = 0.5,
    smi_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        smi_range_window=smi_range_window,
        smi_fast=smi_fast,
        smi_slow=smi_slow,
        base_exposure=base_exposure,
        smi_sensitivity=smi_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
