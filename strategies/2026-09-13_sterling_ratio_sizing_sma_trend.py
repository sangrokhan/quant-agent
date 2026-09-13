"""Strategy: SMA200 trend-following gate with rolling Sterling Ratio
dynamic exposure scaling.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per Wikipedia's Sterling Ratio article (https://en.wikipedia.org/wiki/Sterling_ratio,
read via browser_exec this iteration; web_search found the page directly),
the classic Sterling Ratio = CompoundROR / (Average of the N LARGEST
annual/periodic drawdowns - 10%). Unlike this repo's other risk-measure
sizing overlays tested this cron trigger -- Burke Ratio (root-SUM-of-squares
of every per-bar drawdown, 2026-09-13-052), Pain Ratio (simple average of
EVERY per-bar drawdown, 2026-09-13-051), MAR/Calmar (single worst drawdown,
2026-09-13-047) -- Sterling averages only the K LARGEST DISTINCT drawdown
EPISODES within the window, ignoring shallow/noise drawdowns entirely. This
isolates a "tail-episode-averaging" risk measure: sensitive to the severity
of the worst few sustained pullbacks, but robust to a high count of minor
dips (unlike Burke) and not solely reliant on one single worst event
(unlike MAR).

This strategy scales an SMA(200) trend gate's exposure by the trailing
Sterling ratio of the underlying asset. First Sterling-Ratio-based sizing
strategy in this repo.

Signal logic
------------
- Base directional signal: long when close > SMA(trend_window), flat
  otherwise (identical trend gate to the repo's other sizing-overlay
  strategies, for direct comparability).
- Within each trailing `sterling_window`, identify the underwater
  (drawdown-from-running-peak) series D(t) = (peak-price)/peak. Segment
  it into maximal contiguous runs where D(t) > 0 ("drawdown episodes"),
  take each episode's own max depth, and average the `n_largest` deepest
  episode depths (fewer than n_largest available -> average what exists).
  This differs from Burke (sums ALL per-bar D(t)^2) and Pain (means ALL
  per-bar D(t)) by operating on EPISODE-level maxima, and only the
  largest few, not every bar.
- Annualized return over the same window (mean daily log return * 252).
- Sterling Ratio = annualized_return / (avg_of_n_largest_episode_depths +
  sterling_adjustment), guarded against zero/tiny denominator.
- Exposure: scale = clip(sterling_ratio / sterling_reference, 0,
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


def _episode_depths(dd_window: np.ndarray) -> list:
    """Given one window's underwater series (>=0 values, 0 = at peak),
    return the max depth of each maximal contiguous run where dd > 0."""
    depths = []
    cur_max = 0.0
    in_episode = False
    for v in dd_window:
        if v > 0:
            in_episode = True
            cur_max = max(cur_max, v)
        else:
            if in_episode:
                depths.append(cur_max)
            in_episode = False
            cur_max = 0.0
    if in_episode:
        depths.append(cur_max)
    return depths


def _rolling_sterling_ratio(
    close: pd.Series, window: int, n_largest: int, adjustment: float
) -> pd.Series:
    """Rolling Sterling Ratio: annualized mean daily log return / (average
    of the n_largest deepest drawdown EPISODES within the window +
    adjustment). Uses a simple Python loop over sliding windows (O(n *
    window), acceptable for daily-bar backtests of a few thousand bars)."""
    values = close.to_numpy(dtype=float)
    n = len(values)
    out = np.full(n, np.nan)
    if n < window:
        return pd.Series(out, index=close.index)

    log_ret = np.log(close / close.shift(1)).to_numpy(dtype=float)

    for end in range(window - 1, n):
        start = end - window + 1
        seg = values[start:end + 1]
        running_peak = np.maximum.accumulate(seg)
        dd = (running_peak - seg) / running_peak
        depths = _episode_depths(dd)
        if not depths:
            avg_depth = 0.0
        else:
            depths_sorted = sorted(depths, reverse=True)[:n_largest]
            avg_depth = float(np.mean(depths_sorted))

        ret_seg = log_ret[start:end + 1]
        mean_daily_ret = np.nanmean(ret_seg)
        annualized_ret = mean_daily_ret * 252.0

        denom = avg_depth + adjustment
        out[end] = annualized_ret / denom if denom > 1e-6 else np.nan

    return pd.Series(out, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    sterling_window: int = 90,
    n_largest: int = 3,
    sterling_adjustment: float = 0.10,
    sterling_reference: float = 0.5,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    sterling = _rolling_sterling_ratio(close, sterling_window, n_largest, sterling_adjustment)

    raw_exposure = (sterling / sterling_reference).astype(float)
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
