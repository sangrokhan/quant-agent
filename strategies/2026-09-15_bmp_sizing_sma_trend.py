"""Strategy: Balance of Market Power (BMP, Igor Livshin, TASC Aug 2000)
as a CONTINUOUS SIZING dial inside an SMA(trend_window) uptrend gate,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id 2026-09-15-111):
Per TASC Aug 2000 Traders' Tips (fully disclosed MetaStock formula, via
https://forum.metastock.com/posts/m149845findunread-Aug-2000--Balance-of-Market-Power),
Igor Livshin's Balance of Market Power decomposes each bar's intrabar
buy/sell pressure three ways -- reward based on the open
((H-O)/(H-L) bullish, (O-L)/(H-L) bearish), reward based on the close
((C-L)/(H-L) bullish, (H-C)/(H-L) bearish), and reward based on the
open-close body direction (full body range attributed to whichever side
the bar closed) -- then averages the three bullish rewards and the three
bearish rewards and takes the difference: BMP = avg(bullish) -
avg(bearish), naturally bounded in [-1, 1] per bar, typically smoothed
with a short moving average (source suggests a 14-period SMA). This is a
genuinely new indicator family in this repo (0 prior matches) and, unlike
OBV/CMF/A-D-Line, uses no volume at all -- purely each bar's own
open/high/low/close geometry. Since BMP is already naturally bounded
[-1,1] by construction (no z-score/tanh squashing needed, unlike many
other continuous-dial strategies in this repo), it is used directly as a
sizing dial: exposure = base_exposure + sensitivity*smoothed_BMP, gated by
an SMA(trend_window) uptrend filter with a deadband to cut turnover,
following this repo's established continuous-sizing-dial pattern,
leverage-cap-aware for crypto from the start.

Source: https://forum.metastock.com/posts/m149845findunread-Aug-2000--Balance-of-Market-Power

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


def _compute_bmp(df: pd.DataFrame) -> pd.Series:
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    open_ = df["open"] if "open" in df.columns else df["close"]
    close = df["close"]

    thl = (high - low).replace(0.0, 1e-5)

    bull_reward_open = (high - open_) / thl
    bear_reward_open = (open_ - low) / thl

    bull_reward_close = (close - low) / thl
    bear_reward_close = (high - close) / thl

    is_up_body = close > open_
    bull_reward_oc = np.where(is_up_body, (close - open_) / thl, 0.0)
    bear_reward_oc = np.where(is_up_body, 0.0, (open_ - close) / thl)

    bmp = (
        (bull_reward_open + bull_reward_close + bull_reward_oc) / 3.0
        - (bear_reward_open + bear_reward_close + bear_reward_oc) / 3.0
    )
    return pd.Series(bmp, index=df.index)


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
    smooth_window: int = 14,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    BMP is naturally bounded [-1,1] per bar (Livshin's own construction);
    smoothed with a rolling mean (source's suggested 14-period SMA) then
    used directly (no z-score/tanh needed) as a sizing dial gated by an
    SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    bmp = _compute_bmp(df)
    bmp_smoothed = bmp.rolling(smooth_window).mean()

    raw_exposure = base_exposure + sensitivity * bmp_smoothed
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    smooth_window: int = 14,
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
        smooth_window=smooth_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
