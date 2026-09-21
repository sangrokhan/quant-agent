"""Strategy: Blended dual-horizon momentum gate + realized-vol crash-brake.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-032):
Per a Reddit r/algotrading post ("Update: 3-Factor Leveraged Model
(Momentum + Breadth + Volatility) Backtested 1999-2026", visited this
iteration via browser_exec Google SERP fallback -- web_search DDGS backend
TLS-erroring), the author's own disclosed mechanical rules were:

  Factor 1 -- Momentum (binary in/out gate): exit to cash when a BLENDED
  trend-health score (0.7 * 6-month trailing return + 0.3 * 12-month
  trailing return) drops below the risk-free rate, OR when the 3-month
  annualized return drops below zero.

  Factor 3 -- Volatility (crash brake): force an immediate exit to cash
  whenever trailing 6-month realized (annualized) volatility exceeds a 30%
  threshold.

Factor 2 (an internal breadth-based LEVERAGE-SIZING dial using a
market-wide MMFI breadth series and swapping between 2x/3x leveraged ETF
proxies) is explicitly CROSS-SECTIONAL / requires external breadth data not
available via this repo's single-symbol OHLCV data/loaders.py, so it is
dropped -- this test isolates Factors 1 and 3 only (the two mechanically
disclosed, single-symbol-feasible rules) as a long/flat (no leverage) gate
on the underlying asset itself, rather than reproducing the leveraged-ETF
construction (out of scope per this repo's long-only, no-leverage-product
default and SAFETY.md).

This is distinct from this repo's existing single-lookback SMA/ROC trend
filters (100+ prior entries) via the BLENDED two-horizon momentum score
(0.7*6mo + 0.3*12mo, source's own explicit weighting) combined with BOTH an
absolute risk-free-rate comparison and a short-horizon (3mo) sign check,
and from the existing volatility-regime-gate family (50+ prior entries,
mostly percentile-rank-based) via the source's own ABSOLUTE fixed 30%
annualized-vol threshold (not a rolling percentile).

Signal logic
------------
- mom_score(t) = 0.7 * trailing_6mo_return(t) + 0.3 * trailing_12mo_return(t)
  (source's own weighting; ~126/252 trading days as 6mo/12mo proxies).
- risk_free_rate: a small constant annualized rate (source implies T-bill
  yield; parameterized here, default 0.02 = 2%, converted to the same
  6-month-equivalent basis as mom_score for direct comparison).
- mom_3m(t) = trailing_3mo_return(t) (~63 trading days).
- realized_vol_6m(t) = annualized realized volatility of daily log returns
  over the trailing ~126 trading days.
- Long (position=1) only when ALL of:
    mom_score(t) >= risk_free_rate_6m_equiv
    AND mom_3m(t) >= 0
    AND realized_vol_6m(t) <= vol_threshold (default 0.30)
  Flat (position=0) otherwise (any factor failing forces cash, matching
  source's own "exits to 100% cash" / "forces an immediate exit to 100%
  cash" disclosed override language for both factors).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series {0,1}
    generate_returns(price_df, **params) -> pd.Series daily strategy returns
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    window_3m: int = 63,
    window_6m: int = 126,
    window_12m: int = 252,
    risk_free_rate_annual: float = 0.02,
    vol_window: int = 126,
    vol_threshold: float = 0.30,
) -> pd.Series:
    """Return a {0,1} long/flat position series per the blended momentum +
    volatility crash-brake gate described in the module docstring."""
    df = _prep(price_df)
    close = df["close"]

    ret_3m = close / close.shift(window_3m) - 1.0
    ret_6m = close / close.shift(window_6m) - 1.0
    ret_12m = close / close.shift(window_12m) - 1.0

    mom_score = 0.7 * ret_6m + 0.3 * ret_12m

    # Risk-free rate expressed on the same ~6-month basis as mom_score's
    # dominant (0.7-weighted) horizon, for a like-for-like comparison.
    rf_6m_equiv = risk_free_rate_annual * (window_6m / 252.0)

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)

    momentum_ok = (mom_score >= rf_6m_equiv) & (ret_3m >= 0.0)
    vol_ok = realized_vol <= vol_threshold

    position = (momentum_ok & vol_ok).fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
