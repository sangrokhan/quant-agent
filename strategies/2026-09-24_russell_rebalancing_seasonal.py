"""Strategy: Russell 2000 rebalancing seasonal effect, long-only,
calendar-based (once per year).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://www.quantifiedstrategies.com/quantitative-trading-strategies/
(QuantifiedStrategies.com, "8 Quantitative Trading Strategies" article,
browser_exec -- exact rules disclosed in the article body, not behind the
site's usual member paywall this time).

Source's own disclosed rules and statistics:
    "Russell 2000 rebalances their holdings once per year on the fourth
    Friday of June, and during this period, Russell 2000 has performed
    very well. Not only Russell 2000, but also the broader market, like
    S&P 500... we might argue the outperformance is explained mainly by
    the small-cap effect."
    Trading rules (verbatim):
        "Buy on the close of the first trading day after the 23rd of
        June. Sell on the close on the first trading day of July."
    Source's own disclosed backtest statistics (RUT cash index):
        Average gain per trade: 1.34%. Win ratio: 76%. Average winner:
        2.3%. Average loser: 1.8%. Max drawdown: 6%. Profit factor: 4.1.

This strategy implements the source's own disclosed rules exactly, using
this repo's equity loader on IWM (the small-cap Russell 2000 ETF proxy,
since this repo's data/loaders.py wraps yfinance and RUT the cash index
is not directly tradeable) as the source itself notes RUT was used for
its own backtest but the effect is also visible in the broader market.

First seasonal/calendar strategy in this repo keyed specifically to the
Russell 2000 annual reconstitution date (late June) -- distinct from
every other calendar effect already tested (turn-of-month, Santa Claus
rally, Sell in May, January effect, pre-holiday, FOMC, etc. all key off
different calendar windows).

Signal logic (numeric proxy for the source's disclosed identification
guidelines)
------------------------------------------------------------------------
1. Entry: the first trading day (close) strictly after June 23rd of each
   year (i.e. June 24th or the next available trading day if June 24th
   is a weekend/holiday).
2. Exit: the first trading day (close) of July of the same year.
3. Long-only, one trade per year, fully in cash the rest of the year.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)

Note on params: this strategy's "parameters" are calendar offsets
(entry_day_of_month, exit at start of following month) rather than
numeric thresholds -- the grid test in Step 6 varies the entry/exit day
offsets by a few days each way to probe sensitivity around the source's
exact disclosed dates, consistent with RESEARCH_LOOP.md's requirement
that generate_signals/generate_returns accept tunable params via kwargs.
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


def generate_signals(
    price_df: pd.DataFrame,
    entry_day_of_month: int = 23,
    entry_month: int = 6,
    exit_day_of_month: int = 1,
    exit_month: int = 7,
) -> pd.Series:
    """Return a {0,1} long/flat position series: long from the first
    trading day strictly after `entry_month`/`entry_day_of_month` through
    the first trading day of `exit_month`, each year."""
    df = _prep(price_df)
    idx = df.index
    n = len(idx)

    position = np.zeros(n, dtype=int)

    years = sorted(set(idx.year))
    for year in years:
        # entry: first trading day strictly after entry_day_of_month of entry_month
        entry_cutoff = pd.Timestamp(year=year, month=entry_month, day=entry_day_of_month, tz=idx.tz)
        entry_candidates = idx[idx > entry_cutoff]
        entry_candidates = entry_candidates[
            (entry_candidates.year == year) & (entry_candidates.month == entry_month)
        ]
        if len(entry_candidates) == 0:
            continue
        entry_ts = entry_candidates[0]
        entry_pos = idx.get_loc(entry_ts)

        # exit: first trading day of exit_month (same year, or next year if exit_month < entry_month)
        exit_year = year if exit_month >= entry_month else year + 1
        exit_candidates = idx[
            (idx.year == exit_year)
            & (idx.month == exit_month)
            & (idx.day >= exit_day_of_month)
        ]
        if len(exit_candidates) == 0:
            continue
        exit_ts = exit_candidates[0]
        exit_pos = idx.get_loc(exit_ts)

        if isinstance(entry_pos, slice) or isinstance(exit_pos, slice):
            continue
        if exit_pos <= entry_pos:
            continue

        position[entry_pos:exit_pos + 1] = 1

    return pd.Series(position, index=idx)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
