"""Strategy: Regime-conditional 12-1 vs 12-0 skip-month momentum switch.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-016):
Per Dikhit (Jan 2026), "The Informational Role of the Most Recent Month in
Industry-Level Momentum Strategies" (summarized by Larry Swedroe/Alpha
Architect, https://www.interactivebrokers.com/campus/ibkr-quant-news/the-
skip-month-mystery-what-last-months-returns-are-really-telling-you/),
examining Fama-French 48-industry portfolios 1975-2024: the classic 12-1
("skip-month") momentum signal (12mo return excluding the most recent
month) outperforms strongly in a "Stable Trend" regime (prior month's own
return was above its trailing average AND prior month's realized
volatility was below its trailing average) -- 2.32% avg monthly return in
that regime for 12-1. But 12-1 degrades sharply and gets beaten by the
12-0 ("include-month") variant specifically when the PRIOR MONTH's
volatility spiked (Stress/Crash regime: 12-1 only 0.94% vs 12-0's 1.35%).

This repo has an existing plain 12-1 skip-month momentum entry
(2026-09-09-032, rejected) and an overnight-hold 12-1 variant
(2026-09-16-108/109), but no prior test of this specific REGIME-SWITCHING
construction: using the skip-month (12-1) momentum signal when trailing
short-term realized volatility is calm, and falling back to the
include-month (12-0) momentum signal when trailing short-term realized
volatility is elevated -- addressing the paper's own finding rather than
using either momentum variant unconditionally.

Signal logic
------------
- mom_lookback (default 252 trading days ~ 12 months) and
  skip_days (default 21 trading days ~ 1 month) approximate the monthly
  12-1/12-0 construction on daily bars.
- mom_12_1 = close.shift(skip_days) / close.shift(mom_lookback) - 1
  (return from ~12mo ago to ~1mo ago, excluding the most recent month)
- mom_12_0 = close / close.shift(mom_lookback) - 1
  (full trailing ~12mo return, including the most recent month)
- vol_window-day realized volatility of daily log returns, compared to its
  own trailing vol_lookback-day median -> "elevated vol" when current vol
  > vol_regime_ratio * trailing median (mirrors the paper's own-asset
  prior-month-volatility regime split, adapted to a rolling daily basis
  rather than discrete calendar months).
- Effective momentum signal = mom_12_0 when in the elevated-vol regime,
  else mom_12_1 (calm-vol regime) -- picks whichever construction the
  paper found more robust in that state.
- Long when the effective momentum signal > 0, gated additionally by a
  simple long-term trend filter (close > SMA(trend_window)) to avoid
  buying deeply negative-price full-mom-0 signals in structural
  downtrends; flat otherwise.
- Monthly-cadence rebalance approximated by only re-evaluating the signal
  every rebalance_days trading days (default 21, ~1 month) to mirror the
  source's monthly rebalance convention and control turnover/costs; the
  position is held flat between rebalance dates once set.
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
    mom_lookback: int = 252,
    skip_days: int = 21,
    vol_window: int = 21,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
    trend_window: int = 200,
    rebalance_days: int = 21,
) -> pd.Series:
    """Return a {0,1} long/flat position series, rebalanced monthly."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    elevated_vol = (realized_vol > (vol_median * vol_regime_ratio)).fillna(False)

    mom_12_1 = (close.shift(skip_days) / close.shift(mom_lookback)) - 1.0
    mom_12_0 = (close / close.shift(mom_lookback)) - 1.0
    effective_mom = mom_12_0.where(elevated_vol, mom_12_1)

    trend_sma = close.rolling(trend_window).mean()
    trend_ok = close > trend_sma

    raw_long = (effective_mom > 0) & trend_ok.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    current = 0
    for i in range(n):
        if i % rebalance_days == 0:
            current = 1 if bool(raw_long.iloc[i]) else 0
        position.iloc[i] = current
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
