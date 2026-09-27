"""Strategy: Platinum (PPLT) July-seasonality long-only calendar filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-086):
Per https://seasonalitylab.com/stocks/PPLT (browser_exec; web_search for
"platinum PPLT seasonality" surfaced this source directly): abrdn Physical
Platinum Shares ETF (PPLT) shows a "moderate seasonal pattern" over 10
years of data (2016-2025) -- best month July (+2.4% avg return, up 70% of
years / 7 of 10), worst month June (-1.0% avg, up only 30% of years / 3 of
10). The source's own "reality check" flags this pattern as WEAKENING (last
5 years: July closed higher only 40% of the time, median -0.3%, vs 70%/+
3.1% over the full 10-year window) -- this repo tests it anyway per the
standard practice of testing disclosed seasonal claims even when the source
itself is skeptical, since the grid test's vol-regime/param breakdown is
exactly the kind of out-of-sample-style check that would reveal whether the
apparent weakening shows up as a low pass_fraction.

Encodes the direct testable calendar interpretation: long PPLT only during
the disclosed strong month (July, default), flat all other months, with a
configurable comma-separated month list to allow the grid to also test the
full month-inclusive-exclusive variants disclosed (Jan/Apr/May/Jul/Oct/Dec
were all >=50% win rate with positive avg return per the source's own
month-by-month vs-S&P breakdown).

First platinum/PPLT-specific seasonality strategy in this repo (distinct
from 2026-09-17-055 PPLT/PALL ratio regime filter, which uses a relative-
value ratio z-score, not calendar seasonality).

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
    strong_months: str = "7",
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long during the calendar months listed in strong_months
    (comma-separated month numbers, default "7" = July per the source's
    disclosed best-month claim); flat during all other months.
    """
    df = _prep(price_df)
    months_set = {int(m.strip()) for m in strong_months.split(",") if m.strip()}
    in_strong_month = df.index.month.isin(months_set)
    position = pd.Series(in_strong_month.astype(int), index=df.index)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    position = generate_signals(price_df, **kwargs)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
