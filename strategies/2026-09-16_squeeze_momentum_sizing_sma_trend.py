"""Strategy: SMA(trend_window) directional gate with continuous LazyBear
Squeeze Momentum Indicator (SMI) sizing overlay + deadband, leverage-cap-
aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
This repo has 1 prior LazyBear Squeeze Momentum Indicator entry
(2026-09-04-126, strategies/2026-09-04_squeeze_momentum_ema_filter.py):
a binary "enter on first squeeze-release bar with rising positive momentum
above EMA-50" trigger per enlightenedstocktrading.com's systematic rule --
rejected (QQQ decisive fail, SPY near-miss, crypto rejected). That entry only
used the momentum histogram to GATE a binary entry on the specific
squeeze-release event; it never used the momentum histogram's own magnitude
as a continuous sizing signal. This iteration reuses the identical momentum-
histogram construction (close minus the average of the rolling Donchian
midpoint and SMA, run through a rolling linear-regression fit -- LazyBear's
own formula, source unchanged) but reframes it as a CONTINUOUS SIZING dial:
rolling-z-scored + tanh-squashed to [-1,1], used directly as an exposure
dial inside an SMA(trend_window) uptrend gate with a deadband, dropping the
squeeze-detection/release-event gating entirely (continuous entries/exits
driven purely by momentum magnitude, not a single release-bar trigger).
First Squeeze-Momentum-as-continuous-sizing-dial strategy in this repo.

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


def _linreg_value(series: pd.Series, window: int) -> pd.Series:
    x = np.arange(window)
    x_mean = x.mean()
    denom = ((x - x_mean) ** 2).sum()

    def _fit_last(y: np.ndarray) -> float:
        y_mean = y.mean()
        slope = ((x - x_mean) * (y - y_mean)).sum() / denom
        intercept = y_mean - slope * x_mean
        return slope * (window - 1) + intercept  # predicted value at the last point

    return series.rolling(window).apply(_fit_last, raw=True)


def _momentum_histogram(df: pd.DataFrame, mom_window: int) -> pd.Series:
    """LazyBear's Squeeze Momentum histogram (unchanged from
    strategies/2026-09-04_squeeze_momentum_ema_filter.py): close minus the
    average of the rolling Donchian midpoint and SMA, linear-regression
    fitted over mom_window."""
    close, high, low = df["close"], df["high"], df["low"]
    highest_high = high.rolling(mom_window).max()
    lowest_low = low.rolling(mom_window).min()
    donchian_mid = (highest_high + lowest_low) / 2.0
    sma_close = close.rolling(mom_window).mean()
    raw_mom_input = close - (donchian_mid + sma_close) / 2.0
    return _linreg_value(raw_mom_input, mom_window)


def _zscore_tanh(raw: pd.Series, zscore_window: int) -> pd.Series:
    roll_mean = raw.rolling(zscore_window).mean()
    roll_std = raw.rolling(zscore_window).std().replace(0, np.nan)
    zscore = (raw - roll_mean) / roll_std
    return np.tanh(zscore.fillna(0.0))


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
    mom_window: int = 20,
    zscore_window: int = 100,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    exposure = clip(base_exposure + sensitivity*dial, 0, cap), gated to 0
    whenever close is below its SMA(trend_window).
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    raw_mom = _momentum_histogram(df, mom_window=mom_window)
    dial = _zscore_tanh(raw_mom, zscore_window=zscore_window)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    mom_window: int = 20,
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
        mom_window=mom_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
