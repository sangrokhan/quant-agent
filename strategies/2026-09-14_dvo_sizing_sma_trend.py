"""Strategy: SMA(trend_window) directional gate with continuous David Varadi
Oscillator (DVO) sizing overlay + deadband, leverage-cap-aware for crypto
from the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
This repo's only prior DVO entry (2026-09-08-035) used DVO as a binary
oversold-threshold mean-reversion entry (DVO<15 => buy, gated by
close>SMA(200)). DVO is naturally bounded [0,100] by construction (it IS a
rolling percent-rank), so this iteration reframes it as a CONTINUOUS SIZING
dial: rescaled to [-1,+1] via (DVO-50)/50, directly used as an exposure
dial within an SMA(trend_window) uptrend gate -- reusing this cron
trigger's now well-established bounded-oscillator-as-sizing-dial pattern
(RVI/CMO/TII/AO/BW-MFI-ROC/etc all flipped from binary reject/near-miss to
accepted continuous-sizing variants this way).

Source: same DVO formula as 2026-09-08-035
(https://www.quantifiedstrategies.com/david-varadi-oscillator/ --
detrended = SMA(sma_window, Close/MedianPrice), DVO =
100*PercentRank(detrended, rank_lookback)); only the *use* is new.

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


def _dvo(high: pd.Series, low: pd.Series, close: pd.Series, sma_window: int, rank_lookback: int) -> pd.Series:
    median_price = (high + low) / 2.0
    ratio = close / median_price
    detrended = ratio.rolling(sma_window).mean()
    # Rolling percent-rank (0-100), vectorized via pandas rank(pct=True) over
    # each rolling window's own values -- equivalent to the original
    # 2026-09-08-035 apply-based percent-rank but much faster for grid tests.
    dvo = detrended.rolling(rank_lookback).apply(
        lambda w: (pd.Series(w).rank(pct=True).iloc[-1]) * 100.0, raw=False
    )
    return dvo.fillna(50.0).clip(lower=0.0, upper=100.0)


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
    sma_window: int = 3,
    rank_lookback: int = 126,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    DVO is bounded [0,100] by construction; rescaled to [-1,+1] via
    (DVO-50)/50, then used directly as a sizing dial within the
    SMA(trend_window) uptrend gate.
    """
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    dvo = _dvo(high, low, close, sma_window, rank_lookback)
    dvo_centered = (dvo - 50.0) / 50.0

    raw_exposure = base_exposure + sensitivity * dvo_centered
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    sma_window: int = 3,
    rank_lookback: int = 126,
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
        sma_window=sma_window,
        rank_lookback=rank_lookback,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
