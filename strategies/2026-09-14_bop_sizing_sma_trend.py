"""Strategy: SMA(trend_window) directional gate with continuous Balance of
Power (BOP) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-099):
Balance of Power (Igor Livshin, August 2001; formula per DuckDuckGo HTML
SERP results from tradingview.com, wealthcharts.com, agenatrader.com -- all
consistent): BOP = (Close - Open) / (High - Low), smoothed with a rolling
mean to reduce day-to-day choppiness. Naturally bounded in [-1, 1] by
construction (the numerator's magnitude cannot exceed the denominator's
range). This repo has 2 prior BOP entries: a binary threshold-crossover
(2026-09-04-071, decisively rejected, explicitly noted as "highly
parameter-sensitive") and a divergence variant (2026-09-10-107, accepted).
Neither used BOP as a CONTINUOUS SIZING dial. This iteration applies the
same reframing that rescued VZO/ADX/DMI-diff/CHOP/Vortex/TSI/RMI/SMI earlier
this cron trigger: within an SMA(trend_window) uptrend gate, exposure scales
continuously with smoothed BOP level rather than triggering a discrete
threshold-cross entry -- directly testing whether the earlier threshold
rejection's "highly parameter-sensitive" verdict was a symptom of the
binary-threshold construction (small changes in the entry level flipping
trade count/timing) rather than BOP itself lacking signal, since a
continuous dial has no single brittle threshold to be sensitive to.

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


def _bop(df: pd.DataFrame, smoothing_window: int = 14) -> pd.Series:
    """Smoothed BOP = SMA((Close-Open)/(High-Low), smoothing_window),
    bounded [-1, 1] by construction (numerator can't exceed denominator's
    range in magnitude)."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    open_ = df["open"]

    range_ = (high - low).replace(0, np.nan)
    raw_bop = (close - open_) / range_
    smoothed = raw_bop.rolling(smoothing_window).mean()
    return smoothed.clip(lower=-1.0, upper=1.0)


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
    bop_smoothing_window: int = 14,
    base_exposure: float = 0.5,
    bop_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover. Default deadband
    is wider than most other sizing-dial strategies in this repo (0.15 vs
    0.05-0.10) because BOP's inherent day-to-day choppiness needs stronger
    turnover control to survive transaction costs -- see
    backtests/2026-09-14_bop_sizing_sma_trend.md."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    bop = _bop(df, smoothing_window=bop_smoothing_window)  # already ~[-1, 1]

    raw_exposure = base_exposure + bop_sensitivity * bop
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    bop_smoothing_window: int = 14,
    base_exposure: float = 0.5,
    bop_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        bop_smoothing_window=bop_smoothing_window,
        base_exposure=base_exposure,
        bop_sensitivity=bop_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
