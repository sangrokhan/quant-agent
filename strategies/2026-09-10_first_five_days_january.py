"""Strategy: First Five Days of January indicator (Stock Trader's Almanac).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-025):
Per Stock Trader's Almanac (studied back to 1950, cited by CNBC 2020-01-02):
"When stocks finish the first five [trading] days [of January] higher, the
S&P 500 has been positive more than 80% of the time at year-end with an
average gain of about 13%." The mechanical rule tested here: sum the
returns of the first 5 trading days of each January; if the cumulative
return over those 5 days is positive, hold long for the REMAINDER of the
year (day 6 of January through the last trading day of December); if
negative, stay flat for the rest of the year. Re-evaluate every January.

Distinct from the already-accepted January Barometer (2026-09-10-019),
which uses the ENTIRE month of January's own return as the signal — this
strategy uses only the first 5 trading days (a much shorter, earlier
signal window), and holds from day 6 of January onward (one month earlier
than the Barometer's February start) rather than from February.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(price_df: pd.DataFrame, num_days: int = 3) -> pd.Series:
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
        if len(jan_closes) <= num_days:
            continue  # not enough January bars to evaluate the signal

        # Cumulative return over the first `num_days` trading days of
        # January (day 0 close to day num_days close).
        first_five_return = (jan_closes.iloc[num_days] / jan_closes.iloc[0]) - 1.0

        # Apply the regime from the (num_days+1)-th trading day of January
        # through the end of the calendar year.
        signal_start_date = jan_closes.index[num_days]
        rest_of_year_mask = (idx >= signal_start_date) & (years == yr)

        if first_five_return > 0:
            position.loc[rest_of_year_mask] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(price_df, **params)
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    return strat_returns
