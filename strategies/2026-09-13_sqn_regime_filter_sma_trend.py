"""Strategy: SMA200 trend-following gate combined with a rolling System
Quality Number (SQN, Van Tharp) binary regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per tradesviz.com / quantstrategy.io / journalplus.co (Google SERP snippets,
browser_exec; web_search DuckDuckGo backend returned zero results for the
direct query): System Quality Number (Van Tharp) =
sqrt(N) * (Expectancy / StdDev_of_R_multiples), where R-multiples normalize
each trade's outcome by a fixed risk unit. This is structurally distinct
from every other sizing-overlay ratio already tested in this repo (Sharpe/
Sortino/Omega/UPI/Rachev/Tail/Burke/Pain/Sterling/Treynor/Kappa/Cornish-
Fisher-Sharpe/Coefficient-of-Variation): those all scale exposure
CONTINUOUSLY and proportionally to the ratio's magnitude. SQN's own
sqrt(N)-scaling (rewarding a LARGER sample of consistent trades, not just a
higher per-trade ratio) makes it naturally suited as a BINARY regime
quality-filter (trade only when the trailing SQN estimate exceeds a quality
threshold, flat otherwise) rather than a proportional sizing dial -- this
iteration tests SQN in that on/off filter role for the first time in this
repo, layered on top of the same SMA(200) trend gate used by every other
sizing-overlay strategy here for direct comparability.

Signal logic
------------
- Base directional signal: long-candidate when close > SMA(trend_window).
- R-multiple proxy for each day: daily log return divided by a fixed risk
  unit = the trailing (long, non-overlapping with SQN window) rolling
  standard deviation of NEGATIVE daily log returns only (a fixed risk-per-
  unit stand-in for "initial stop distance" in Van Tharp's original
  per-trade formulation, since this repo's OHLCV daily-bar strategies don't
  have discrete per-trade risk amounts).
- Over each trailing `sqn_window`, SQN = sqrt(sqn_window) *
  mean(R-multiples) / std(R-multiples).
- Regime gate: long only when trend_long AND trailing SQN > sqn_threshold;
  flat otherwise (fully binary allocation, no continuous scaling -- exposure
  is 0 or `leverage_cap`).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (values in
    {0, leverage_cap}).
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


def _risk_unit(log_ret: pd.Series, risk_window: int) -> pd.Series:
    """Trailing stdev of negative daily log returns only (fixed risk unit,
    Van Tharp R-multiple denominator stand-in)."""
    neg = log_ret.where(log_ret < 0)
    risk = neg.rolling(risk_window, min_periods=10).std()
    return risk


def _rolling_sqn(
    log_ret: pd.Series, risk_unit: pd.Series, sqn_window: int
) -> pd.Series:
    """Rolling SQN = sqrt(N) * mean(R) / std(R), R = log_ret / risk_unit."""
    r_multiple = (log_ret / risk_unit.replace(0, np.nan)).to_numpy(dtype=float)
    n = len(r_multiple)
    out = np.full(n, np.nan)
    if n < sqn_window:
        return pd.Series(out, index=log_ret.index)

    for end in range(sqn_window - 1, n):
        start = end - sqn_window + 1
        seg = r_multiple[start:end + 1]
        seg = seg[~np.isnan(seg)]
        if len(seg) < 10:
            continue
        std = float(np.std(seg))
        if std <= 1e-8:
            continue
        mean = float(np.mean(seg))
        out[end] = np.sqrt(len(seg)) * mean / std

    return pd.Series(out, index=log_ret.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    risk_window: int = 60,
    sqn_window: int = 60,
    sqn_threshold: float = 1.0,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a binary {0, leverage_cap} exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    log_ret = np.log(close / close.shift(1))
    risk_unit = _risk_unit(log_ret, risk_window)
    sqn = _rolling_sqn(log_ret, risk_unit, sqn_window)

    quality_ok = (sqn > sqn_threshold).fillna(False)
    long_now = trend_long.fillna(False) & quality_ok
    position = pd.Series(
        np.where(long_now, leverage_cap, 0.0), index=close.index
    )
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
