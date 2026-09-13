"""Strategy: SMA200 trend-following gate with rolling Burke Ratio (root-
sum-square drawdown) dynamic exposure scaling.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per the Burke Ratio (Burke Ratio = (PortfolioReturn - RiskFreeRate) /
sqrt(sum(D_i^2)), confirmed via Google AI Overview synthesis of
QuantMemo/LuxAlgo/Wharton sources, read via browser_exec this iteration
after web_search returned zero results): the Burke ratio uses the
root-SUM-of-squares of ALL distinct drawdown events within a window,
NOT the root-MEAN-of-squares (which is the Ulcer Index, already tested in
this repo, 2026-09-04-144/2026-09-10-045). This means Burke's denominator
scales with the NUMBER of drawdown events as well as their individual
depth -- a strategy/asset with many small drawdowns gets penalized more
under Burke than under Ulcer Index (which normalizes by count), making
Burke sensitive to drawdown FREQUENCY in addition to depth in a way none
of this repo's other risk-measure sizing overlays this cron trigger
capture directly.

This strategy scales an SMA(200) trend gate's exposure by the trailing
Burke ratio of the underlying asset, isolating this frequency-sensitive
risk-measure as a sizing signal. First Burke-Ratio-based strategy in this
repo.

Signal logic
------------
- Base directional signal: long when close > SMA(trend_window), flat
  otherwise (identical trend gate to the repo's other sizing-overlay
  strategies).
- Within each trailing `burke_window`, identify individual drawdown
  events: a drawdown event is a maximal contiguous run where price is
  below its running peak (within the window); D_i is that event's own
  max drawdown depth (peak-to-trough within the run). Burke's raw risk
  term = sqrt(sum(D_i^2)) over all such events in the window.
- Approximation for tractable vectorization: rather than segmenting exact
  contiguous underwater runs (expensive per-window), this implementation
  uses the standard practical simplification widely used in retail Burke-
  ratio implementations: treat every bar's drawdown-from-peak value D(t)
  as one observation and compute sqrt(sum(D(t)^2)) over the window (this
  is the discrete "Burke Ratio" formula as commonly implemented, distinct
  from Ulcer Index's sqrt(MEAN(D(t)^2)) purely by the sum-vs-mean
  normalization -- the SUM formulation is what makes Burke sensitive to
  the number of underwater bars, i.e. drawdown duration/frequency, not
  just depth).
- Annualized return over the same window (mean daily log return * 252).
- Burke Ratio = annualized_return / sqrt(sum(D(t)^2)) (guarded against
  zero/tiny denominator).
- Exposure: scale = clip(burke_ratio / burke_reference, 0, leverage_cap).
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


def _rolling_burke_ratio(close: pd.Series, window: int) -> pd.Series:
    """Rolling Burke Ratio: annualized mean daily log return / sqrt(sum of
    squared per-bar drawdowns within the window), vectorized via numpy
    sliding windows."""
    values = close.to_numpy(dtype=float)
    n = len(values)
    out = np.full(n, np.nan)
    if n < window:
        return pd.Series(out, index=close.index)

    price_windows = np.lib.stride_tricks.sliding_window_view(values, window)
    running_peak = np.maximum.accumulate(price_windows, axis=1)
    drawdowns = (running_peak - price_windows) / running_peak
    sum_sq_dd = np.nansum(drawdowns ** 2, axis=1)
    burke_denom = np.sqrt(sum_sq_dd)

    log_ret = np.log(close / close.shift(1)).to_numpy(dtype=float)
    ret_windows = np.lib.stride_tricks.sliding_window_view(log_ret, window)
    mean_daily_ret = np.nanmean(ret_windows, axis=1)
    annualized_ret = mean_daily_ret * 252.0

    with np.errstate(divide="ignore", invalid="ignore"):
        burke = np.where(burke_denom > 1e-6, annualized_ret / burke_denom, np.nan)

    out[window - 1:] = burke
    return pd.Series(out, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    burke_window: int = 90,
    burke_reference: float = 0.3,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    burke = _rolling_burke_ratio(close, burke_window)

    raw_exposure = (burke / burke_reference).astype(float)
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
