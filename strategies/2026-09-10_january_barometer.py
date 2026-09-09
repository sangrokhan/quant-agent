"""Strategy: January Barometer (Yale Hirsch, 1972) annual regime rule.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-019):
Per the January Barometer (Yale Hirsch, 1972, popularized in the Stock
Trader's Almanac; corroborated by andersoneminitrading.com's disclosed
stat: "Since 1945, the S&P has risen in price during the month of January
63% of the time. When price rose [in January], the rest of the year also
tended to rise"): "As goes January, so goes the year." The mechanical
rule: at the close of the last trading day of January, check whether
January's own return (close on last day of January vs. close on last day
of the PRIOR December) was positive. If positive, hold long for the
remainder of the calendar year (February through December); if negative,
stay flat for the remainder of the year. Re-evaluate every January.

Distinct from all 4 prior calendar-seasonality entries in this repo
(Santa Claus Rally 2026-09-05-008 -- a fixed ~7-trading-day window
regardless of any prior signal; January Effect 2026-09-06-133 -- trades
the FIRST days of January itself as a small-cap effect, not a signal
FROM January used to trade the REST of the year; Turn-of-Month/Day-of-Week
-- unrelated shorter-horizon mechanisms) via its once-a-year,
whole-remaining-year regime-switch construction: this is the only
strategy in this repo that makes exactly one binary decision per calendar
year based on a single month's own return, then holds that position for
up to 11 months.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def generate_signals(price_df: pd.DataFrame) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    idx = df.index

    years = idx.year
    months = idx.month

    position = pd.Series(0, index=df.index, dtype=int)

    unique_years = sorted(set(years))
    for yr in unique_years:
        jan_mask = (years == yr) & (months == 1)
        if not jan_mask.any():
            continue
        jan_closes = close[jan_mask]
        # January's own return: last close in January vs. first close in January
        # (approximating "close on last day of prior December" with the
        # first available close in January when December data isn't in range)
        prior_dec_mask = (years == yr - 1) & (months == 12)
        if prior_dec_mask.any():
            start_price = close[prior_dec_mask].iloc[-1]
        else:
            start_price = jan_closes.iloc[0]
        end_jan_price = jan_closes.iloc[-1]
        jan_return = (end_jan_price / start_price) - 1.0

        # apply the regime for Feb-Dec of this same year
        rest_of_year_mask = (years == yr) & (months >= 2)
        if jan_return > 0:
            position.loc[rest_of_year_mask] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(price_df, **params)
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    return strat_returns
