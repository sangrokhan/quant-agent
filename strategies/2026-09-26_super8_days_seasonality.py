"""Strategy: Stock Trader's Almanac "Super 8 Days" seasonality.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD), sourced from
github.com/paappraiser/almanac-trading-strategies (README, read via
browser_exec after web_extract returned no content for the GitHub URL --
DDGS backend is search-only). The repo's rule catalogue (s704 "Super 8
Days") describes the Stock Trader's Almanac's own finding that "First 2 +
last 3 + mid-month 9-11 [trading days] capture most gains" of the monthly
seasonal pattern -- i.e. of the ~21 trading days in an average month, only
these 8 specific trading-day-of-month slots (by rank, not calendar date)
account for most of the month's net positive drift, while the remaining
~13 days are seasonally flat/negative on average.

Distinct from the already-rejected-as-near-miss Turn-of-Month strategy
(2026-09-06-169, Lakonishok & Smidt 1988: last trading day of month through
3rd trading day of next month, i.e. a single ~4-day contiguous window) and
from Mid-Month Bulge (not yet tested standalone in this repo): Super 8 Days
is the UNION of THREE separate trading-day-rank windows within one month
(first 2 trading days of month, mid-month trading days 9-11, and last 3
trading days of month) rather than one contiguous window -- explicitly
combining turn-of-month with a distinct mid-month institutional-flow
window the Almanac claims is separately positive. First "combined
multi-window intra-month trading-day-rank" seasonality strategy in this
repo.

Interface contract for validators (see validation/validators.py) and grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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
    first_n_days: int = 2,
    last_n_days: int = 3,
    mid_start_day: int = 9,
    mid_end_day: int = 11,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long on any trading day whose 1-indexed rank within its calendar month
    (counting from the start) is in {1..first_n_days} OR
    {mid_start_day..mid_end_day} OR whose rank from month-END is in
    {1..last_n_days}; flat all other trading days.
    """
    df = _prep(price_df)
    idx = df.index
    ym = pd.Series(idx.year * 100 + idx.month, index=idx)

    rank_from_start = ym.groupby(ym).cumcount() + 1  # 1-indexed
    rank_from_end = ym.groupby(ym).cumcount(ascending=False) + 1  # 1-indexed

    in_first = rank_from_start <= first_n_days
    in_last = rank_from_end <= last_n_days
    in_mid = (rank_from_start >= mid_start_day) & (rank_from_start <= mid_end_day)

    pos = (in_first | in_last | in_mid).astype(int)
    pos.index = idx
    return pos


def generate_returns(
    price_df: pd.DataFrame,
    first_n_days: int = 2,
    last_n_days: int = 3,
    mid_start_day: int = 9,
    mid_end_day: int = 11,
) -> pd.Series:
    """Daily strategy returns, position lagged by 1 day to avoid look-ahead."""
    df = _prep(price_df)
    pos = generate_signals(
        df,
        first_n_days=first_n_days,
        last_n_days=last_n_days,
        mid_start_day=mid_start_day,
        mid_end_day=mid_end_day,
    )
    price_col = "close" if "close" in df.columns else df.columns[0]
    daily_ret = df[price_col].pct_change()
    strat_ret = pos.shift(1).fillna(0) * daily_ret
    return strat_ret.fillna(0.0)
