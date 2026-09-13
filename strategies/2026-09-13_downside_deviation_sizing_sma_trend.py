"""Strategy: SMA200 trend-following gate with downside-deviation (Sortino-
style semi-variance) inverse-risk position sizing.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per https://urbandigistore.com/blog/stop-loss-position-sizing-sortino-deviation
(read via browser_exec this iteration), downside deviation (semi-variance,
sigma_d = sqrt(mean(min(0, R_i - T)^2)) for a target acceptable return T,
typically 0) only penalizes returns BELOW the target threshold, unlike
standard deviation which penalizes both upside and downside variance
equally. The source's rationale: sizing by downside deviation instead of
full stddev should give steadier, higher-upside-skew assets/strategies a
LARGER allocation than a symmetric vol-targeting scheme would, since
upside spikes no longer inflate the risk denominator.

This repo already has an accepted symmetric inverse-volatility-targeting
overlay (2026-09-08-165, stddev-based) on the same SMA(200) trend gate --
this iteration isolates whether swapping the sizing denominator from
symmetric realized stddev to asymmetric downside deviation (semi-variance)
changes performance, since QQQ/SPY/BTC all have historically exhibited
positive skew during uptrends (the exact condition where this asymmetric
measure should differ most from the symmetric one). First
downside-deviation/semi-variance-based position-sizing strategy in this
repo (distinct from the Sortino-style entry-filter idea, since this is a
pure continuous-exposure SIZING mechanism, not a discrete Sortino-ratio
threshold entry/exit signal).

Signal logic
------------
- Base directional signal: long when close > SMA(trend_window), flat
  otherwise (same trend gate as the repo's other sizing-overlay
  strategies).
- Rolling downside deviation over `dd_window` days of daily returns,
  target_return=0.0 (standard Sortino convention, per source): sigma_d =
  sqrt(mean(min(0, r_i - target_return)^2)).
- Exposure: scale = clip(target_downside_dev / sigma_d, 0, leverage_cap).
  Applied only while the trend gate is long.

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


def _rolling_downside_deviation(daily_ret: pd.Series, window: int, target_return: float = 0.0) -> pd.Series:
    """Rolling downside deviation (semi-variance) of daily returns,
    vectorized via numpy sliding windows."""
    values = daily_ret.to_numpy(dtype=float)
    n = len(values)
    out = np.full(n, np.nan)
    if n < window:
        return pd.Series(out, index=daily_ret.index)

    windows = np.lib.stride_tricks.sliding_window_view(values, window)
    downside = np.minimum(0.0, windows - target_return)
    with np.errstate(invalid="ignore"):
        semi_var = np.nanmean(downside ** 2, axis=1)
    sigma_d = np.sqrt(semi_var)
    out[window - 1:] = sigma_d
    return pd.Series(out, index=daily_ret.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    dd_window: int = 60,
    target_downside_dev: float = 0.01,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    daily_ret = close.pct_change()
    sigma_d = _rolling_downside_deviation(daily_ret, dd_window)
    sigma_d_safe = sigma_d.replace(0, np.nan)

    raw_exposure = (target_downside_dev / sigma_d_safe).astype(float)
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
