"""Strategy: Sell in May / Halloween Effect calendar seasonality.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Google's AI-overview synthesis of QuantPedia/QuantifiedStrategies pages
(query: "Sell in May Halloween effect strategy specific rules backtest"),
the "Halloween Indicator" documents that equity returns from
November-through-April have historically been materially higher than
returns from May-through-October (Bouman & Jacobsen 1997 and many
replications). Mechanical rule: 100% long equities from Nov 1 to Apr 30,
flat (cash/short-term bonds -- approximated here as simply flat, since this
repo's loaders don't expose a bond-yield cash-return proxy) from May 1 to
Oct 31. First broad 6-month/6-month calendar-seasonality strategy in this
repo -- distinct from the narrower sub-month calendar effects already
tested (Turn-of-Month, January effect, Santa Claus rally), which condition
on specific days rather than a full half-year split.

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
    long_start_month: int = 11,
    long_end_month: int = 4,
) -> pd.Series:
    """Return a {0,1} long/flat position series: long while the calendar
    month is within the [long_start_month .. 12] U [1 .. long_end_month]
    "winter" window (default Nov-Apr), flat during the "summer" window
    (default May-Oct)."""
    df = _prep(price_df)
    months = df.index.month
    if long_start_month <= long_end_month:
        in_window = (months >= long_start_month) & (months <= long_end_month)
    else:
        # Wraps around year-end (e.g. Nov(11) .. Apr(4)).
        in_window = (months >= long_start_month) | (months <= long_end_month)
    position = pd.Series(in_window.astype(int), index=df.index)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
