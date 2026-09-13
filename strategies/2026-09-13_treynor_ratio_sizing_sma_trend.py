"""Strategy: SMA200 trend-following gate with rolling Treynor Ratio dynamic
exposure scaling.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per https://www.investopedia.com/terms/t/treynorratio.asp (read via
browser_exec): Treynor Ratio = (portfolio_return - risk_free_rate) /
beta_of_portfolio (Jack Treynor, CAPM co-inventor). Unlike Sharpe (total
standard deviation) and every drawdown/percentile/CVaR-based sizing overlay
tested this cron trigger (Omega, GPR, Pain, Burke, Sterling, MAR/Calmar,
downside-deviation, CVaR, Tail Ratio, Rachev, K-Ratio), Treynor scales
excess return by SYSTEMATIC risk only (beta vs a market benchmark) --
requiring an external benchmark series rather than being derivable purely
from the asset's own return distribution. This strategy uses SPY as a
fixed cross-asset benchmark (even for the crypto leg, as a genuine
falsification test of whether an equity-market-beta-based sizing signal
has any relevance to BTC/ETH) and scales an SMA(200) trend gate's exposure
by the trailing Treynor ratio. First Treynor-Ratio-based (CAPM-beta) sizing
strategy in this repo.

Signal logic
------------
- Base directional signal: long when close > SMA(trend_window), flat
  otherwise (identical trend gate to the repo's other sizing-overlay
  strategies, for direct comparability).
- Benchmark: SPY daily log returns (fetched via data/loaders.py's
  load_equity, sliced/reindexed to the target asset's own date range).
- Within each trailing `treynor_window`, compute rolling beta =
  cov(asset_returns, benchmark_returns) / var(benchmark_returns), and
  rolling annualized excess return (mean daily log return * 252, risk-free
  assumed 0 for simplicity). Treynor ratio = annualized_excess_return /
  beta, guarded against a near-zero or negative beta (negative-beta
  windows are treated as "ratio not meaningful" per Investopedia and
  exposure is set to 0 for that window, consistent with the source's own
  stated caveat).
- Exposure: scale = clip(treynor_ratio / treynor_reference, 0,
  leverage_cap). Applied only while the trend gate is long.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
"""

from __future__ import annotations

import sys
import os

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402

_benchmark_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_benchmark_log_returns(index: pd.DatetimeIndex) -> pd.Series:
    """Fetch SPY daily log returns (cached across calls within a process)
    and align to the target asset's date index."""
    start = index.min()
    end = index.max()
    cache_key = (pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize())
    if cache_key not in _benchmark_cache:
        bench_df = load_equity("SPY", start=start.to_pydatetime(), end=end.to_pydatetime())
        bench_df = _prep(bench_df)
        bench_log_ret = np.log(bench_df["close"] / bench_df["close"].shift(1))
        _benchmark_cache[cache_key] = bench_log_ret
    return _benchmark_cache[cache_key].reindex(index).fillna(0.0)


def _rolling_treynor_ratio(
    close: pd.Series, benchmark_log_ret: pd.Series, window: int
) -> pd.Series:
    """Rolling Treynor Ratio: annualized mean daily log return / rolling
    beta vs the benchmark. Negative or near-zero beta windows produce NaN
    (treated as "not meaningful" -> zero exposure downstream)."""
    log_ret = np.log(close / close.shift(1))

    cov = log_ret.rolling(window).cov(benchmark_log_ret)
    bench_var = benchmark_log_ret.rolling(window).var()
    beta = cov / bench_var.replace(0.0, np.nan)

    mean_daily_ret = log_ret.rolling(window).mean()
    annualized_ret = mean_daily_ret * 252.0

    treynor = annualized_ret / beta
    treynor = treynor.where(beta > 0.05, other=np.nan)  # negative/near-zero beta not meaningful
    return treynor


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    treynor_window: int = 90,
    treynor_reference: float = 1.0,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    benchmark_log_ret = _get_benchmark_log_returns(close.index)
    treynor = _rolling_treynor_ratio(close, benchmark_log_ret, treynor_window)

    raw_exposure = (treynor / treynor_reference).astype(float)
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
