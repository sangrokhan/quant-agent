"""Strategy: WaveTrend [LazyBear] wt1-wt2 spread as a CONTINUOUS SIZING dial
on SMA(trend_window) trend gate, leverage-cap-aware for crypto.

Hypothesis (this cron trigger's iteration 5, direct fix attempt for
2026-09-17-073's rejected binary crossover version):
2026-09-17-073 tested LazyBear's WaveTrend oscillator (formula per
https://github.com/bnvnvnv/fmzstrategies/blob/master/Indicator-WaveTrend-
Oscillator.md, already confirmed this cron trigger, not re-fetched) as a
binary oversold-crossover entry trigger and it was rejected: too few
trades (24-27 over 7.5yr) to establish a robust full-sample edge despite
decent per-vol-regime cells (Sharpe 2.21 best cell). This iteration
reframes the SAME underlying wt1-wt2 spread (already zero-centered by
construction, no additional normalization needed unlike most raw
oscillators tested elsewhere in this repo) as a CONTINUOUS exposure-sizing
dial within an SMA(trend_window) uptrend gate, the pattern that has
rescued numerous other oscillator binary-trigger near-misses/failures in
this repo (Fisher Transform, KST, Chaikin Oscillator, Awesome Oscillator,
Coppock Curve, etc.) by converting a low-frequency discrete signal into a
continuously-modulated exposure that trades far more often and is less
sensitive to any single threshold-crossing timing.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap])
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _wavetrend(high: pd.Series, low: pd.Series, close: pd.Series, n1: int, n2: int):
    ap = (high + low + close) / 3.0
    esa = ap.ewm(span=n1, adjust=False).mean()
    d = (ap - esa).abs().ewm(span=n1, adjust=False).mean()
    ci = (ap - esa) / (0.015 * d.replace(0.0, np.nan))
    tci = ci.ewm(span=n2, adjust=False).mean()
    wt1 = tci
    wt2 = wt1.rolling(4).mean()
    return wt1, wt2


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
    n1: int = 10,
    n2: int = 21,
    scale: float = 60.0,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    wt1-wt2 spread (zero-centered by construction) is divided by `scale`
    (source's own obLevel1=60 reference magnitude) and tanh-squashed to
    [-1,1], then used as a sizing dial.
    """
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    wt1, wt2 = _wavetrend(high, low, close, n1, n2)
    spread = (wt1 - wt2) / scale
    dial = np.tanh(spread.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    n1: int = 10,
    n2: int = 21,
    scale: float = 60.0,
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
        n1=n1,
        n2=n2,
        scale=scale,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
