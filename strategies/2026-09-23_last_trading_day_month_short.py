"""Strategy: Short the last trading day of the month (intraday open-to-close fade).

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration's id):
Per QuantifiedStrategies.com's "Last Trading Day Of The Month Trading
Strategy (Seasonality)"
(https://www.quantifiedstrategies.com/last-trading-day-of-the-month/), the
LAST trading day of each calendar month is a structurally weak day for the
S&P 500/SPY: the source's own SPY backtest (1993-2021) shows the OPEN-TO-
CLOSE intraday return on that specific day averages -0.11% with only a 42%
win rate (decisively worse than the market's average day), while the prior
close-to-open OVERNIGHT leg into that same day is roughly average (+0.04%).
This isolates the badness specifically to the last trading day's own
intraday session -- distinct from every other overnight/turn-of-month
strategy in this repo (all of which go LONG into month-end via the
overnight leg, e.g. 2026-09-03_turn_of_month.py); this strategy instead
goes SHORT for the intraday open-to-close session ONLY on the single last
trading day of the month, flat all other days including flat overnight.

Signal logic
------------
- Identify the last trading day of each month (the row whose calendar month
  differs from the NEXT row's calendar month, or the last row overall).
- On that day only: short position (-1) for the open-to-close session.
- All other days: flat (0).
- No overnight exposure by construction (flat before the open and after
  the close on non-signal days; the position is entered fresh at the open
  of the signal day and squared off at that same day's close).

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series (position series,
        -1/0, held only intraday on the last trading day of the month)
    generate_returns(price_df, **params) -> pd.Series (daily strategy
        returns using SAME-DAY open-to-close return times the position;
        no shift(1) needed since the position for day t is knowable at
        day t's own open, being purely calendar-driven).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df.index = pd.to_datetime(df.index)
    return df


def _last_trading_day_mask(index: pd.DatetimeIndex) -> pd.Series:
    """True on rows that are the last trading day of their calendar month."""
    months = index.to_period("M")
    next_months = months[1:].append(pd.PeriodIndex([months[-1]]))
    is_last = pd.Series(months.values != next_months.values, index=index)
    # The final row of the whole series is ambiguous (unknown next month) --
    # treat it as NOT a signal to avoid a false positive from truncation.
    if len(is_last) > 0:
        is_last.iloc[-1] = False
    return is_last


def generate_signals(
    price_df: pd.DataFrame,
    allow_short: bool = True,
) -> pd.Series:
    """Return -1 on the last trading day of each month (intraday short), else 0."""
    df = _prep(price_df)
    is_last = _last_trading_day_mask(df.index)

    position = pd.Series(0.0, index=df.index)
    if allow_short:
        position[is_last] = -1.0
    return position.fillna(0.0)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Same-day open-to-close return times the short position (no shift(1) --
    position for day t is determined purely by day t's own calendar date,
    known at market-open, and held only intraday to day t's close)."""
    df = _prep(price_df)
    open_ = df["open"]
    close = df["close"]

    position = generate_signals(price_df, **kwargs)

    intraday_ret = (close - open_) / open_
    strat_ret = position * intraday_ret
    return strat_ret.fillna(0.0)
