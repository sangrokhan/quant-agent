"""Strategy: SMA crossover gated by the Trend Persistence Range (TPR,
Richard Poster, S&C Feb 2021, via Financial Hacker), long-only.

Hypothesis (knowledge_base id 2026-09-15-115):
Per Financial Hacker
(https://financial-hacker.com/petra-on-programming-the-trend-persistence-indicator/),
Richard Poster's Trend Persistence Range measures how consistently an
SMA's slope has pointed in one direction over a rolling window: over
tpr_period bars, count bars where the SMA(sma_period) slope exceeds
+threshold (CtrP) separately from bars where it falls below -threshold
(CtrM); TPR = 100 * |CtrP - CtrM| / tpr_period, a 0-100 trend-persistence
measure (smoothed with a short EMA per the source's own replication
choice). Source's own honest finding: using TPR as a filter on top of a
plain SMA crossover system nearly doubled returns in an IN-SAMPLE-
optimized backtest, but a follow-up walk-forward-optimized retest showed
"much less" improvement -- source explicitly flags the in-sample result
as likely overstated. First TPR entry in this repo (0 prior matches).
This iteration tests TPR as a trend-strength gate (TPR > threshold) on an
SMA(fast)/SMA(slow) crossover, with this repo's own out-of-sample
walk-forward validator providing the honest check the source's own MT4
backtest lacked.

Source: https://financial-hacker.com/petra-on-programming-the-trend-persistence-indicator/

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position).
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


def _tpr(close: pd.Series, sma_period: int, tpr_period: int, slope_threshold: float, smooth_span: int) -> pd.Series:
    sma = close.rolling(sma_period).mean()
    slope = sma.diff()

    is_up = (slope > slope_threshold).astype(float)
    is_down = (slope < -slope_threshold).astype(float)

    ctr_p = is_up.rolling(tpr_period).sum()
    ctr_m = is_down.rolling(tpr_period).sum()

    tpr_raw = 100.0 * (ctr_p - ctr_m).abs() / tpr_period
    tpr_smoothed = tpr_raw.ewm(span=smooth_span, adjust=False).mean()
    return tpr_smoothed


def generate_signals(
    price_df: pd.DataFrame,
    fast_sma_period: int = 20,
    slow_sma_period: int = 50,
    tpr_sma_period: int = 20,
    tpr_period: int = 15,
    tpr_threshold: float = 30.0,
    smooth_span: int = 5,
) -> pd.Series:
    """Long-only: hold whenever fast SMA > slow SMA (crossover state, not
    just the crossing bar) AND the TPR trend-persistence filter exceeds
    tpr_threshold (avoid trading through choppy/non-trending regimes).
    """
    df = _prep(price_df)
    close = df["close"]

    slope_threshold = 0.0001 * close.rolling(tpr_sma_period).mean()  # ~1bp-of-price threshold, scale-adaptive analog of the source's fixed "1 pip"
    fast_sma = close.rolling(fast_sma_period).mean()
    slow_sma = close.rolling(slow_sma_period).mean()
    crossover_long = fast_sma > slow_sma

    # TPR uses a fixed absolute threshold in the source; here scale by
    # price level (median threshold over the sample) since this repo
    # trades multiple assets at very different price scales.
    sma_for_tpr = close.rolling(tpr_sma_period).mean()
    sma_slope = sma_for_tpr.diff()
    typical_slope_scale = sma_slope.abs().rolling(252, min_periods=60).median()
    slope_thr = 0.1 * typical_slope_scale  # 10% of typical slope magnitude, source's "1 pip" analog

    is_up = (sma_slope > slope_thr).astype(float)
    is_down = (sma_slope < -slope_thr).astype(float)
    ctr_p = is_up.rolling(tpr_period).sum()
    ctr_m = is_down.rolling(tpr_period).sum()
    tpr_raw = 100.0 * (ctr_p - ctr_m).abs() / tpr_period
    tpr = tpr_raw.ewm(span=smooth_span, adjust=False).mean()

    long_condition = (crossover_long & (tpr > tpr_threshold)).fillna(False)
    return long_condition.astype(float)


def generate_returns(
    price_df: pd.DataFrame,
    fast_sma_period: int = 20,
    slow_sma_period: int = 50,
    tpr_sma_period: int = 20,
    tpr_period: int = 15,
    tpr_threshold: float = 30.0,
    smooth_span: int = 5,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        fast_sma_period=fast_sma_period,
        slow_sma_period=slow_sma_period,
        tpr_sma_period=tpr_sma_period,
        tpr_period=tpr_period,
        tpr_threshold=tpr_threshold,
        smooth_span=smooth_span,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
