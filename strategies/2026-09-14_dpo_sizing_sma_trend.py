"""Strategy: SMA(trend_window) directional gate with continuous Detrended
Price Oscillator (DPO) sizing overlay + deadband, leverage-cap-aware for
crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Detrended Price Oscillator (DPO, per ChartSchool/Investopedia/TradingView):
    DPO_t = Close_{t - (n/2 + 1)} - SMA_n(Close)_t
i.e. the close price from n/2+1 bars ago minus the n-period SMA. Unlike
OBV/PVT/ADL (cumulative running totals that are nonstationary and needed a
rate-of-change reframing this cron trigger), DPO is ALREADY a bounded
oscillator centered on zero by construction (it strips the trend out via the
displaced SMA), so it can be used AS-IS (no diff/roc needed) as a continuous
sizing dial. This repo has 3 prior DPO entries (2026-09-04-056 binary
crossover; 2026-09-06-139 trough/peak-turn timing; 2026-09-08-049
cycle-timing+quantile-regime-gate), none using DPO directly as a continuous
z-scored sizing multiplier. This iteration: rolling z-score of raw DPO,
tanh-squashed to [-1,+1], used as a sizing dial within an SMA(trend_window)
uptrend gate, with a deadband to cut turnover and a leverage_cap for crypto.

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


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    dpo_window: int = 20,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Raw DPO (already a zero-centered bounded-ish oscillator, no diff needed)
    is rolling-z-scored over `zscore_window` bars and tanh-squashed to
    [-1,+1] before use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    shift = dpo_window // 2 + 1
    sma = close.rolling(dpo_window).mean()
    dpo = close.shift(shift) - sma  # DPO defined at "current" index using data up to shift bars ago; no lookahead since shift>=1

    roll_mean = dpo.rolling(zscore_window).mean()
    roll_std = dpo.rolling(zscore_window).std()
    zscore = (dpo - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
        raw = raw_exposure.fillna(0.0).to_numpy()
        held = np.zeros_like(raw)
        current = 0.0
        for i, r in enumerate(raw):
            if abs(r - current) > deadband:
                current = r
            held[i] = current
        return pd.Series(held, index=raw_exposure.index)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    dpo_window: int = 20,
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
        dpo_window=dpo_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
