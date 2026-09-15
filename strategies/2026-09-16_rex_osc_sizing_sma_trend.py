"""Strategy: SMA(trend_window) directional gate with continuous REX
Oscillator sizing overlay + deadband, leverage-cap-aware for crypto from
the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per quantifiedstrategies.com's REX Oscillator article
(https://www.quantifiedstrategies.com/rex-oscillator/, already
visited/logged in this repo's ledger from id 2026-09-08-059; formula
re-used unchanged, no new fetch this iteration): TVB ("True Value of a
Bar") = 3*Close - (Low + Open + High), REX = EMA(TVB, rex_period),
oscillating around zero. This repo's one prior REX entry
(strategies/2026-09-08_rex_oscillator_pullback_continuation.py, id
2026-09-08-059) used REX as a binary pullback-continuation zero-cross
trigger (gated by an active-pullback lookback state), rejected decisively
on both equity symbols and crypto. This iteration reframes the identical
REX/TVB formula as a CONTINUOUS SIZING dial: raw REX is unbounded (a
volume-free bar-strength measure, no natural [0,1]/[-1,1] scale), so it's
rolling-z-scored and tanh-squashed to [-1,1], used as a sizing multiplier
inside an SMA(trend_window) uptrend gate -- following this cron trigger's
established continuous-sizing-dial pattern. First REX-Oscillator-as-
continuous-sizing-dial strategy in this repo.

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


def _rex_oscillator(df: pd.DataFrame, rex_period: int) -> pd.Series:
    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    tvb = 3 * close - (low + open_ + high)
    return tvb.ewm(span=rex_period, adjust=False).mean()


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
    rex_period: int = 21,
    zscore_window: int = 100,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    exposure = clip(base_exposure + sensitivity*tanh(rex_zscore), 0, cap)
    gated to 0 whenever close is below its SMA(trend_window).
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    raw_rex = _rex_oscillator(df, rex_period)

    roll_mean = raw_rex.rolling(zscore_window).mean()
    roll_std = raw_rex.rolling(zscore_window).std()
    zscore = (raw_rex - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)
    raw_exposure = raw_exposure.where(~zscore.isna(), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    rex_period: int = 21,
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
        rex_period=rex_period,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
