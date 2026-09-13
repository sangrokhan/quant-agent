"""Strategy: SMA200 trend-following gate with rolling K-Ratio (Kestner)
dynamic exposure scaling.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per Investopedia (https://www.investopedia.com/terms/k/kratio.asp) and
WallStreetMojo (https://www.wallstreetmojo.com/k-ratio/), both read via
browser_exec this iteration (web_search worked for keyword discovery but
quantifiedstrategies.com's page failed a bot-check when opened via
browser_exec, so it was logged as visited-but-unhelpful and Investopedia/
WallStreetMojo were used instead): Lars Kestner's K-Ratio (1996, revised
2003/2013) is NOT a drawdown-based or distribution-shape-based risk measure
like every other sizing overlay tested earlier this cron trigger (Omega,
Gain-to-Pain, Pain Ratio, Burke Ratio, Sterling Ratio, MAR/Calmar,
downside-deviation, CVaR). Instead it fits a LINEAR REGRESSION of
log(cumulative return) against time over a trailing window and computes
slope / (standard_error_of_slope * sqrt(n)) -- i.e. it rewards a smooth,
consistently-trending equity curve and penalizes a choppy/volatile one even
if final drawdown and Sharpe are similar. This isolates "trend consistency"
（regression-based)  as a distinct sizing signal from every risk-measure
overlay tested so far in this repo. First K-Ratio-based strategy (entry or
sizing) in this repo.

Signal logic
------------
- Base directional signal: long when close > SMA(trend_window), flat
  otherwise (identical trend gate to the repo's other sizing-overlay
  strategies, for direct comparability).
- Within each trailing `kratio_window`, compute the cumulative log-return
  curve (VAMI proxy) and regress it against a simple time index (0..w-1)
  via OLS. K-ratio = slope / (std_err_of_slope * sqrt(w)) — the
  "modern" (2003+) Kestner formulation that normalizes by sample size so
  the metric is comparable across window lengths, guarded against a
  degenerate (near-zero) standard error.
- Exposure: scale = clip(k_ratio / k_ratio_reference, 0, leverage_cap).
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


def _rolling_k_ratio(close: pd.Series, window: int) -> pd.Series:
    """Rolling K-Ratio: OLS-regress the log-cumulative-return curve against
    a simple time index within each trailing window; K-ratio =
    slope / (std_err_of_slope * sqrt(window)). Uses a simple Python loop
    over sliding windows (O(n * window), acceptable for daily-bar
    backtests of a few thousand bars)."""
    values = close.to_numpy(dtype=float)
    n = len(values)
    out = np.full(n, np.nan)
    if n < window:
        return pd.Series(out, index=close.index)

    log_ret = np.log(values[1:] / values[:-1])
    log_ret = np.concatenate([[0.0], log_ret])  # align length, first bar = 0
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_centered = x - x_mean
    sxx = float(np.sum(x_centered ** 2))

    for end in range(window - 1, n):
        start = end - window + 1
        seg_log_ret = log_ret[start:end + 1]
        cum_log_ret = np.cumsum(seg_log_ret)  # VAMI proxy (log space)

        y = cum_log_ret
        y_mean = y.mean()
        y_centered = y - y_mean

        if sxx <= 1e-12:
            continue
        slope = float(np.sum(x_centered * y_centered) / sxx)
        intercept = y_mean - slope * x_mean
        residuals = y - (intercept + slope * x)
        dof = window - 2
        if dof <= 0:
            continue
        resid_var = float(np.sum(residuals ** 2) / dof)
        std_err_slope = np.sqrt(resid_var / sxx) if sxx > 0 else np.nan

        if std_err_slope is None or np.isnan(std_err_slope) or std_err_slope < 1e-8:
            continue
        k_ratio = slope / (std_err_slope * np.sqrt(window))
        out[end] = k_ratio

    return pd.Series(out, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    kratio_window: int = 90,
    k_ratio_reference: float = 0.5,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    k_ratio = _rolling_k_ratio(close, kratio_window)

    raw_exposure = (k_ratio / k_ratio_reference).astype(float)
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
