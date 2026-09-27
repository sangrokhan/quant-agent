"""Strategy: Coffee (KC=F) futures monthly seasonality -- long during
historically strong months (April, May, December), flat otherwise.

Hypothesis (2026-09-27 KB entry, this iteration): per
https://www.quantifiedstrategies.com/coffee-trading-strategy/, "coffee
futures have been noted to perform better during the months of April, May,
and December than during the months of June and September" (per the
source's own seasonality chart). This iteration encodes the direct
testable calendar interpretation: long coffee futures (KC=F) only during
the disclosed strong months (default April, May, December), flat during
all other months (including the disclosed weak months June/September).
First coffee-futures-specific strategy in this repo (0 prior KB hits on
coffee/KC=F specifically).

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
    strong_months: str = "4,5,12",
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long during the calendar months listed in strong_months (comma-separated
    month numbers, default "4,5,12" = April, May, December per the source's
    disclosed seasonality); flat during all other months.
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
    # shift position by 1 to avoid lookahead: today's return earned by
    # yesterday's end-of-day position
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
