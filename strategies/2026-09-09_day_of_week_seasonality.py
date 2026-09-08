"""Strategy: Day-of-week / weekend-effect calendar seasonality.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Google's synthesized search results (Investopedia/ScienceDirect/
QuantifiedStrategies) on the "day of the week effect" / "weekend effect":
equity returns have historically differed systematically by day of week --
Monday returns tend to be the weakest (the "weekend effect", partly
attributed to negative news accumulating over the weekend / short-covering
dynamics), while returns later in the week (commonly Wednesday-Friday) tend
to be relatively stronger. Mechanical rule tested here: be long only on a
configurable subset of weekdays (`long_weekdays`, default Wed/Thu/Fri =
{2,3,4} in pandas' Monday=0 convention), flat on the remaining days
(default Mon/Tue). First day-of-week (sub-week) calendar-seasonality
strategy in this repo -- distinct from all month-level calendar effects
(Turn-of-Month, January effect, Santa Claus rally, Sell-in-May) already
tested, which condition on month/day-of-month rather than day-of-week.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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
    long_weekdays: tuple = (2, 3, 4),
) -> pd.Series:
    """Return a {0,1} long/flat position series: long only on the weekdays
    in `long_weekdays` (pandas convention: Monday=0 ... Sunday=6), flat on
    all other weekdays."""
    df = _prep(price_df)
    weekday = df.index.weekday
    in_window = pd.Series(weekday, index=df.index).isin(list(long_weekdays))
    position = in_window.astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
