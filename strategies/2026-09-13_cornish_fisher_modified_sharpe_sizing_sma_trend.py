"""Strategy: SMA200 trend-following gate with rolling Cornish-Fisher
Modified Sharpe Ratio dynamic exposure scaling.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per https://investmenttoolkit.wordpress.com/2014/10/29/modified-sharpe-ratio-in-excel/
(read via browser_exec Google SERP fallback; other sources -- braverock.com,
metricgate.com -- 404'd/403'd): the Modified Sharpe Ratio (Gregoriou &
Gueyie 2003 convention) = (return - risk_free) / Modified VaR (MVaR), where
MVaR uses the Cornish-Fisher asymptotic expansion to adjust the normal
z-score by the return distribution's own skewness (S) and excess kurtosis
(K):
    z_cf = z + (z^2-1)*S/6 + (z^3-3z)*K/24 - (2z^3-5z)*S^2/36
    MVaR = -(mu + z_cf * sigma)
Unlike every prior sizing overlay tested this cron trigger (which use
empirical percentiles/CVaR/drawdown-RMS/regression-fit directly), this
ANALYTICALLY approximates the left-tail risk via the first FOUR moments
(mean, variance, skewness, kurtosis) of the trailing return distribution --
a fundamentally different estimation approach (parametric moment-expansion
vs. empirical/nonparametric). First Cornish-Fisher-Modified-Sharpe-based
sizing strategy in this repo. Scales an SMA(200) trend gate's exposure by
the trailing Modified Sharpe Ratio.

Signal logic
------------
- Base directional signal: long when close > SMA(trend_window), flat
  otherwise (identical trend gate to the repo's other sizing-overlay
  strategies, for direct comparability).
- Within each trailing `cf_window`, compute mean (mu), std dev (sigma),
  skewness (S), and excess kurtosis (K) of daily log returns. Compute the
  Cornish-Fisher-adjusted z-score at a fixed confidence level (default
  95%, z=-1.645) and the resulting Modified VaR (daily, then annualized by
  sqrt(252)/252 scaling consistent with mu/sigma's own annualization).
- Modified Sharpe = annualized_mean_return / (annualized_MVaR +
  adjustment), guarded against a near-zero/negative denominator.
- Exposure: scale = clip(modified_sharpe / msr_reference, 0, leverage_cap).
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


def _rolling_modified_sharpe(
    close: pd.Series, window: int, z_base: float, adjustment: float
) -> pd.Series:
    """Rolling Cornish-Fisher Modified Sharpe Ratio: annualized mean
    return / annualized Cornish-Fisher-adjusted Modified VaR. Uses
    pandas' vectorized rolling mean/std/skew/kurt (fast, no per-window
    Python loop) instead of scipy.stats.skew/kurtosis called per window."""
    log_ret = np.log(close / close.shift(1))

    mu = log_ret.rolling(window).mean()
    sigma = log_ret.rolling(window).std(ddof=1)
    s = log_ret.rolling(window).skew()  # sample skewness (pandas default, close to scipy's bias-adjusted)
    k = log_ret.rolling(window).kurt()  # sample excess kurtosis (pandas default, normal=0)

    z = z_base
    z_cf = (
        z
        + (z ** 2 - 1) * s / 6.0
        + (z ** 3 - 3 * z) * k / 24.0
        - (2 * z ** 3 - 5 * z) * (s ** 2) / 36.0
    )
    mvar_daily = -(mu + z_cf * sigma)  # positive = expected loss magnitude

    annualized_mean = mu * 252.0
    annualized_mvar = mvar_daily * np.sqrt(252.0)

    denom = annualized_mvar + adjustment
    modified_sharpe = annualized_mean / denom
    modified_sharpe = modified_sharpe.where((denom > 1e-6) & (sigma > 1e-10), other=np.nan)
    return modified_sharpe


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    cf_window: int = 90,
    z_base: float = -1.645,
    adjustment: float = 0.01,
    msr_reference: float = 0.1,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    modified_sharpe = _rolling_modified_sharpe(close, cf_window, z_base, adjustment)

    raw_exposure = (modified_sharpe / msr_reference).astype(float)
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
