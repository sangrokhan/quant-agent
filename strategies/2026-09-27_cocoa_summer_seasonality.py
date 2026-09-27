"""Strategy: Cocoa (CC=F) futures monthly seasonality -- long during
summer months (historically strong), flat during spring/fall (historically
weak).

Hypothesis (2026-09-27 KB entry, this iteration): per
https://www.quantifiedstrategies.com/cocoa-trading-strategy/, "Cocoa
futures tend to perform better during the summer months than any other
period of the year. The contracts tend to do poorly in spring and fall"
(per the source's own seasonality chart). This iteration encodes the
direct testable calendar interpretation: long cocoa futures (CC=F) only
during the disclosed strong summer months (default June, July, August),
flat during all other months. First cocoa-futures-specific strategy in
this repo (0 prior KB hits on cocoa/CC=F specifically). Distinct from the
already-rejected coffee monthly seasonality test (2026-09-27-070, different
commodity, different months).

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
    strong_months: str = "6,7,8",
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long during the calendar months listed in strong_months
    (comma-separated month numbers, default "6,7,8" = June, July, August
    per the source's disclosed summer-seasonality claim); flat during all
    other months.
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
