"""Strategy: SMA(trend_window) directional gate with continuous MAD-scaled
robust z-score sizing overlay + deadband, leverage-cap-aware for crypto.

Hypothesis (this cron trigger):
Direct fix attempt for id 2026-09-21-210 (MAD-scaled robust z-score
mean-reversion, per metricgate.com's MAD-Scaled Z-Score explainer,
z=(ret-median)/(1.4826*MAD)): that binary entry/exit rule was rejected on
full-sample Sharpe (best 0.660, SPY entry_z=2.5/trend_window=200) despite an
unusually broad grid pass_fraction (0.403, both asset classes, all 3 vol
terciles) -- suggesting a real but too-weak-for-binary-trading signal. This
iteration reframes the same robust z-score as a CONTINUOUS SIZING dial
(tanh-squashed) inside an SMA(trend_window) uptrend gate + deadband -- the
pattern that has rescued many other binary near-miss indicators in this
repo (Disparity Index, VAMA, DPO, Hurst, VHF, TII, RVI). Since the raw
robust z is already an interpretable "how extreme is today's return"
measure (not bounded), tanh-squashing it (rather than an additional
z-score-of-z-score) keeps it simple: strongly negative z (outlier down day)
-> dial pushes exposure UP (buy the dip), strongly positive z (outlier up
day) -> dial pushes exposure DOWN (fade). First MAD-robust-zscore
continuous-sizing variant in this repo.

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


def _rolling_mad(x: np.ndarray) -> float:
    med = np.median(x)
    return float(np.median(np.abs(x - med)))


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
    trend_window: int = 200,
    mad_window: int = 40,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.7,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Robust MAD-scaled z-score of daily returns (per metricgate.com formula)
    is tanh-squashed and used, INVERTED (a negative z / outlier-down-day
    increases exposure), as a mean-reversion sizing dial within an
    SMA(trend_window) uptrend gate.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    daily_ret = close.pct_change()
    rolling_median = daily_ret.rolling(mad_window).median()
    rolling_mad = daily_ret.rolling(mad_window).apply(_rolling_mad, raw=True)
    denom = 1.4826 * rolling_mad
    robust_z = (daily_ret - rolling_median) / denom.replace(0, np.nan)

    dial = -np.tanh(robust_z.fillna(0.0))  # invert: negative z -> positive dial

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    mad_window: int = 40,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.7,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        mad_window=mad_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
