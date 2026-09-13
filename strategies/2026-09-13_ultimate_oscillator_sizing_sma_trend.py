"""Strategy: SMA200 trend-following gate with continuous Ultimate Oscillator
(UO) sizing overlay.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-13-077):
Ultimate Oscillator (Larry Williams, 1976) combines Buying Pressure (BP) /
True Range (TR) across three timeframes (default 7/14/28) into a single
0-100 bounded oscillator with a centerline at 50:
  BP = Close - min(Low, PriorClose)
  TR = max(High, PriorClose) - min(Low, PriorClose)
  Avg_n = sum(BP, n) / sum(TR, n)
  UO = 100 * (4*Avg_fast + 2*Avg_mid + Avg_slow) / 7
Per chartschool.stockcharts.com (browser_exec, web_extract blocked by DDGS
search-only backend) and commodity.com/tradingsim.com SERP summaries
(web_search). This repo has 6 prior Ultimate Oscillator entries, all binary
divergence/threshold(30/70) entry triggers. This iteration reuses the
"bounded oscillator as continuous sizing dial" pattern from this cron
trigger's accepted %B/Aroon/Williams %R sizing overlays (071/072/074),
applied to UO's 0-100/centerline-50 construction (structurally distinct: UO
blends THREE timeframes via a weighted BP/TR ratio, unlike any single-window
bounded oscillator tried as a sizing dial so far). exposure =
clip(base_exposure + uo_sensitivity * ((uo-50)/50), 0, leverage_cap) on the
SMA(200) trend gate -- scale exposure up as UO strengthens above its 50
centerline (multi-timeframe buying pressure dominant), down as it weakens
below 50, while the SMA(200) gate keeps the strategy flat outside the
broader uptrend. First Ultimate-Oscillator-as-continuous-sizing strategy in
this repo.

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


def _ultimate_oscillator(
    df: pd.DataFrame, fast: int = 7, mid: int = 14, slow: int = 28
) -> pd.Series:
    close = df["close"]
    high = df["high"]
    low = df["low"]
    prior_close = close.shift(1)

    bp = close - pd.concat([low, prior_close], axis=1).min(axis=1)
    tr = pd.concat([high, prior_close], axis=1).max(axis=1) - pd.concat(
        [low, prior_close], axis=1
    ).min(axis=1)

    avg_fast = bp.rolling(fast).sum() / tr.rolling(fast).sum().replace(0, np.nan)
    avg_mid = bp.rolling(mid).sum() / tr.rolling(mid).sum().replace(0, np.nan)
    avg_slow = bp.rolling(slow).sum() / tr.rolling(slow).sum().replace(0, np.nan)

    uo = 100.0 * (4 * avg_fast + 2 * avg_mid + avg_slow) / 7.0
    return uo


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    uo_fast: int = 7,
    uo_mid: int = 14,
    uo_slow: int = 28,
    base_exposure: float = 0.8,
    uo_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    uo = _ultimate_oscillator(df, fast=uo_fast, mid=uo_mid, slow=uo_slow)

    raw_exposure = base_exposure + uo_sensitivity * ((uo - 50.0) / 50.0)
    exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap).fillna(0.0)

    position = exposure.where(trend_long.fillna(False), other=0.0)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    uo_fast: int = 7,
    uo_mid: int = 14,
    uo_slow: int = 28,
    base_exposure: float = 0.8,
    uo_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        uo_fast=uo_fast,
        uo_mid=uo_mid,
        uo_slow=uo_slow,
        base_exposure=base_exposure,
        uo_sensitivity=uo_sensitivity,
        leverage_cap=leverage_cap,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
