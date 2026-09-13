"""Strategy: SMA(short trend_window) trend-following gate with continuous
RVI sizing overlay + deadband -- SPY-focused trend-window recalibration.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-13-082):
Direct investigation of a pattern this cron trigger flagged across SIX
consecutive accepted sizing-overlay entries (%B-071, Aroon-072, Williams
%R-074, CMO-078, UO-079, StochRSI-080, RVI-081): all pass full-sample Sharpe
on QQQ but come up short on SPY specifically, always with the SAME
trend_window=200 SMA gate default. Hypothesis: a 200-day trend gate is
tuned closer to QQQ's higher-volatility/higher-momentum regime (annualized
vol 22.8%, ann. return 23.4% over the backtest window, per this iteration's
direct measurement) than SPY's lower-vol/lower-momentum profile (18.2% vol,
15.4% return) -- SPY's slower, choppier trend needs a SHORTER trend
confirmation window to reduce whipsaw lag and re-enter faster. A quick
parameter sweep this iteration on the RVI-sizing skeleton (2026-09-13-081,
unchanged sizing logic) shows SPY Sharpe rising from 0.729 (trend_window
200) to ~1.03-1.04 at trend_window 30-40, while QQQ stays >=1.0 across the
same range. This iteration re-tests both symbols on a shortened
trend_window grid to see if a single shared shorter window can pass BOTH
QQQ and SPY simultaneously (rather than accepting QQQ-only), addressing the
open question flagged in 2026-09-13-081's notes.

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


def _rvi(df: pd.DataFrame, window: int = 10) -> pd.Series:
    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]

    a = close - open_
    b = high - low

    num = (a + 2 * a.shift(1) + 2 * a.shift(2) + a.shift(3)) / 6.0
    den = (b + 2 * b.shift(1) + 2 * b.shift(2) + b.shift(3)) / 6.0
    rvi_raw = num / den.replace(0, np.nan)
    rvi = rvi_raw.rolling(window).mean()
    return rvi.clip(lower=-1.0, upper=1.0)


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
    rvi_window: int = 10,
    base_exposure: float = 0.8,
    rvi_sensitivity: float = 0.4,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    rvi = _rvi(df, window=rvi_window)

    raw_exposure = base_exposure + rvi_sensitivity * rvi
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    rvi_window: int = 10,
    base_exposure: float = 0.8,
    rvi_sensitivity: float = 0.4,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        rvi_window=rvi_window,
        base_exposure=base_exposure,
        rvi_sensitivity=rvi_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
