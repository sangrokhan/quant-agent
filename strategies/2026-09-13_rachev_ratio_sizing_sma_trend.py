"""Strategy: SMA200 trend-following gate with rolling Rachev Ratio dynamic
exposure scaling.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per https://metricgate.com/docs/rachev-ratio/ (read via browser_exec after
web_search/DDGS returned no results for the direct query; Google SERP
fallback surfaced this source): the Rachev Ratio (Svetlozar Rachev et al.)
= E[r | r >= q(1-beta)] / -E[r | r <= q(alpha)] -- the ratio of the
CONDITIONAL EXPECTED (CVaR-style) tail GAIN to the conditional expected
tail LOSS. This differs from:
  - the already-tested Tail Ratio (2026-09-13-055 this cron trigger), which
    uses a single PERCENTILE POINT value for each tail, not a conditional
    mean beyond that point;
  - the already-tested CVaR strategy (2026-09-13-045), which only uses the
    LOSS-side CVaR (for inverse vol-style targeting) with no gain-tail
    numerator at all -- Rachev is a genuine reward/risk RATIO of two CVaRs,
    not a single-sided risk budget.
This strategy scales an SMA(200) trend gate's exposure by the underlying
asset's own trailing Rachev ratio. First Rachev-Ratio-based sizing strategy
in this repo.

Signal logic
------------
- Base directional signal: long when close > SMA(trend_window), flat
  otherwise (identical trend gate to the repo's other sizing-overlay
  strategies, for direct comparability).
- Within each trailing `rachev_window`, compute the daily log-return
  distribution's alpha-quantile (loss threshold) and (1-beta)-quantile
  (gain threshold). Rachev ratio = mean(returns >= gain_threshold) /
  -mean(returns <= loss_threshold), guarded against a near-zero/degenerate
  denominator or insufficient tail observations.
- Exposure: scale = clip(rachev_ratio / rachev_reference, 0, leverage_cap).
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


def _rolling_rachev_ratio(
    close: pd.Series, window: int, alpha: float, beta: float, rachev_adjustment: float
) -> pd.Series:
    """Rolling Rachev Ratio: mean of returns above the (1-beta) quantile
    (expected tail gain) divided by minus the mean of returns below the
    alpha quantile (expected tail loss), within each trailing window. Uses
    a simple Python loop over sliding windows (O(n * window), acceptable
    for daily-bar backtests of a few thousand bars)."""
    log_ret = np.log(close / close.shift(1))
    values = log_ret.to_numpy(dtype=float)
    n = len(values)
    out = np.full(n, np.nan)
    if n < window:
        return pd.Series(out, index=close.index)

    for end in range(window - 1, n):
        start = end - window + 1
        seg = values[start:end + 1]
        seg = seg[~np.isnan(seg)]
        if len(seg) < 10:
            continue
        q_loss = np.quantile(seg, alpha)
        q_gain = np.quantile(seg, 1 - beta)
        tail_losses = seg[seg <= q_loss]
        tail_gains = seg[seg >= q_gain]
        if len(tail_losses) == 0 or len(tail_gains) == 0:
            continue
        expected_tail_loss = -float(np.mean(tail_losses))
        expected_tail_gain = float(np.mean(tail_gains))
        denom = expected_tail_loss + rachev_adjustment
        if denom <= 1e-8:
            continue
        out[end] = expected_tail_gain / denom

    return pd.Series(out, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    rachev_window: int = 90,
    alpha: float = 0.05,
    beta: float = 0.05,
    rachev_adjustment: float = 0.001,
    rachev_reference: float = 1.0,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    rachev = _rolling_rachev_ratio(close, rachev_window, alpha, beta, rachev_adjustment)

    raw_exposure = (rachev / rachev_reference).astype(float)
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
