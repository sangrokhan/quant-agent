"""Strategy: Monthly-decision Golden Cross (SMA50>SMA200) regime timing.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-043):
Per SetupAlpha's "This Bitcoin Indicator Turned $10,000 Into $4.7 Million
While Bitcoin Made $3.4 Million" (Sep 6 2026, visited this iteration --
https://setup4alpha.substack.com/p/bitcoin-indicators-ranked): the
source's fully-disclosed test methodology evaluates a regime rule ONCE
PER MONTH (on the last trading day of each month) -- hold the asset for
the entire following month if the regime rule is "on", cash otherwise --
rather than continuously re-evaluating daily. The source's own disclosed
free-tier rule for rank #9 of 17 is the classic Golden Cross
(SMA(50) > SMA(200)), which reached $2,136,221 from $10,000 with only 18
regime switches over 11 years (vs buy-and-hold BTC's $3,442,843 but with
a much shallower max drawdown -- 64.7% vs bitcoin's 83.4%).

This repo has tested SMA(50)>SMA(200) golden-cross trend-following before
(2026-09-03-021 with a vol-percentile gate; T3/Tillson dual-MA crossover
variants), but always with DAILY signal evaluation/continuous
reassessment, never with this source's specific MONTHLY-decision
mechanic (evaluate regime once at month-end, hold verbatim for the whole
following month regardless of intra-month regime flips) -- a genuinely
different rebalance-cadence construction that source's own methodology
credits for much of the switch-count/turnover reduction versus a
continuously-reevaluated daily golden cross. Tested here on both crypto
(BTC/ETH, the source's native domain) and equities (QQQ/SPY, generalization
check) since this repo's grid-test always covers both asset classes.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    fast_sma_window: int = 50,
    slow_sma_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Regime rule (evaluated once per calendar month, at month-end):
    SMA(fast_sma_window) > SMA(slow_sma_window) (golden cross condition).
    If true at a given month-end, hold long for the ENTIRE following
    month regardless of any intra-month crossover flips; if false, hold
    cash for the entire following month. This "decide once per month,
    hold verbatim" mechanic is the source's own disclosed methodology,
    distinct from every other daily-continuously-reevaluated SMA
    crossover already tested in this repo.
    """
    df = _prep(price_df)
    close = df["close"]

    fast_sma = close.rolling(fast_sma_window).mean()
    slow_sma = close.rolling(slow_sma_window).mean()
    golden_cross_on = (fast_sma > slow_sma)

    # Identify month-end rows (last available trading day of each
    # calendar month) and read the regime state there.
    naive_index = close.index.tz_localize(None) if close.index.tz is not None else close.index
    periods = naive_index.to_period("M")
    month_end_pos = pd.Series(range(len(close)), index=close.index).groupby(periods).max()
    month_end_dates = close.index[sorted(month_end_pos.values)]

    regime_at_month_end = golden_cross_on.loc[month_end_dates]

    # Forward-fill the month-end decision to every day of the FOLLOWING
    # month: shift the decision dates forward by one day so ffill starts
    # applying from the first trading day after each month-end.
    decision_series = regime_at_month_end.copy()
    position = decision_series.reindex(close.index, method="ffill").fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
