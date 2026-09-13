"""Strategy: SMA200 trend-following gate with rolling Tail-Ratio dynamic
exposure scaling.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per https://www.pfolio.io/academy/tail-ratio (read via browser_exec;
tradesviz.com's equivalent page hit a Cloudflare 502 and was logged as
visited-but-unhelpful): Tail Ratio = |R(95th percentile)| / |R(5th
percentile)| of a return distribution. It is a PERCENTILE-based asymmetry
measure -- robust to any single extreme outlier (unlike skewness's
cubed-deviation weighting) and structurally distinct from every other
sizing overlay tested this cron trigger (Omega/GPR/Pain/Burke/Sterling/MAR
= drawdown or mean-based; K-ratio = OLS regression fit). Per the source,
trend-following strategies structurally exhibit tail ratios above 1
(long right tail from riding sustained trends, tight left tail from
stop-outs/signal reversal) while vol-selling/mean-reversion strategies
show tail ratios well below 1. This strategy scales an SMA(200) trend
gate's exposure by the asset's OWN trailing tail ratio: when the
trend-follower's structural tail-ratio signature (right tail > left tail)
is currently present in the underlying asset, lean in; when it inverts
(left tail dominates, e.g. crash-prone/choppy regime), reduce exposure.
First Tail-Ratio-based sizing strategy in this repo.

Signal logic
------------
- Base directional signal: long when close > SMA(trend_window), flat
  otherwise (identical trend gate to the repo's other sizing-overlay
  strategies, for direct comparability).
- Within each trailing `tail_window`, compute the daily log-return
  distribution's 95th and 5th percentiles; tail_ratio =
  abs(p95) / abs(p5), guarded against a near-zero denominator.
- Exposure: scale = clip(tail_ratio / tail_ratio_reference, 0,
  leverage_cap). Applied only while the trend gate is long.

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


def _rolling_tail_ratio(
    close: pd.Series, window: int, lower_pct: float, upper_pct: float, tail_adjustment: float
) -> pd.Series:
    """Rolling Tail Ratio = |percentile(upper_pct)| / (|percentile(lower_pct)| +
    tail_adjustment) of the trailing daily log-return distribution."""
    log_ret = np.log(close / close.shift(1))
    p_hi = log_ret.rolling(window).quantile(upper_pct)
    p_lo = log_ret.rolling(window).quantile(lower_pct)
    denom = p_lo.abs() + tail_adjustment
    tail_ratio = p_hi.abs() / denom
    return tail_ratio


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    tail_window: int = 90,
    lower_pct: float = 0.05,
    upper_pct: float = 0.95,
    tail_adjustment: float = 0.001,
    tail_ratio_reference: float = 1.0,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    tail_ratio = _rolling_tail_ratio(close, tail_window, lower_pct, upper_pct, tail_adjustment)

    raw_exposure = (tail_ratio / tail_ratio_reference).astype(float)
    exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap).fillna(0.0)

    position = exposure.where(trend_long.fillna(False), other=0.0)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
