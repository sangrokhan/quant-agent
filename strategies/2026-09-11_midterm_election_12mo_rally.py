"""Strategy: Post-Midterm-Election 12-Month Rally.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-080):
Per QuantifiedStrategies.com's disclosed rule
(https://www.quantifiedstrategies.com/sp500-midterm-election-year/,
visited this iteration): U.S. midterm elections occur every 4 years,
halfway through a presidential term (even years NOT divisible by 4:
1994, 1998, 2002, ..., 2010, 2014, 2018, 2022). Per U.S. Bank/E*TRADE
data the source cites, the S&P 500 has averaged a 16.3% return in the
12 months following a midterm election (Oct-to-Oct or Nov-to-Nov,
depending on exact source window), with NO negative 12-month return
since 1939 across 15 midterm cycles studied.

Signal logic
------------
- Long the primary asset from November 1st of a midterm-election year
  (year % 4 == 2, e.g. 1994, 1998, ..., 2018, 2022) through October 31st
  of the following year (a 12-month hold).
- Flat all other times.

This is the first MIDTERM-election-cycle (as opposed to the already-
tested 4-year PRESIDENTIAL-election-cycle year-1-through-4 seasonality,
2026-09-08-163) calendar strategy in this repo -- a narrower, specifically
midterm-anchored 12-month window rather than a full-term year
classification.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} long/flat)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _is_midterm_year(year: int) -> bool:
    return year % 4 == 2


def generate_signals(
    price_df: pd.DataFrame,
    start_month: int = 11,
    hold_months: int = 12,
) -> pd.Series:
    """Return a {0,1} daily long/flat position series."""
    df = _prep(price_df)
    index = pd.to_datetime(df.index).tz_localize(None)

    position = pd.Series(0, index=df.index, dtype=int)

    years = sorted(set(index.year))
    for year in years:
        if not _is_midterm_year(year):
            continue
        window_start = pd.Timestamp(year=year, month=start_month, day=1)
        window_end = window_start + pd.DateOffset(months=hold_months)
        mask = (index >= window_start) & (index < window_end)
        position.iloc[mask] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
