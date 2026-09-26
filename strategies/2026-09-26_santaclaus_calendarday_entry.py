"""Strategy: Santa Claus Rally, calendar-DAY entry variant (not trading-day-rank).

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD), sourced from
quantifiedstrategies.com's "Santa Claus Rally In The Stock Market" article
(https://www.quantifiedstrategies.com/santa-claus-rally-in-stocks/, read via
browser_exec after web_extract failed -- DDGS backend is search-only and
cannot extract URL content). The source discloses THREE variants of the
Santa Claus Rally rule; this repo's prior entry (2026-09-05-008, rejected,
0/48 grid cells) only tested the classic "last 5 trading days of December +
first 2 trading days of January" (trading-day-RANK-from-month-boundary)
definition.

This strategy tests the source's own "backtest 3" variant instead, which is
mechanically DIFFERENT (a fixed CALENDAR-day-of-month entry trigger, not a
trading-day rank counted from month start/end): go long at the close of the
first trading day strictly after calendar day `entry_calendar_day` of
December (source uses entry_calendar_day=20), and exit at the close of the
`exit_trading_day_jan`'th trading day of the new year (source uses the FIRST
trading day of January, i.e. exit_trading_day_jan=1). Source's own backtest
(Amibroker, S&P 500, since 1960) reports: average gain 1%, win ratio 67%,
profit factor 4.5, max drawdown 5.9% -- notably its BEST-looking variant of
the three disclosed (vs. backtest 1's win ratio 66%/profit factor 2, and
backtest 2's win ratio 72%/profit factor 4 using an options-expiration-week
entry instead).

Distinct from 2026-09-05-008: that strategy is long during "last N trading
days of Dec" (a trailing-N-trading-day RANK window ending at month-end,
independent of the actual calendar date December falls on that year); this
strategy instead anchors the entry to a literal calendar day-of-month
number (the 20th), so in years where December has an unusual trading
calendar (holidays shifting things) the exact entry timing differs, and
critically the exit is anchored to "1st trading day of January" (a single
trading day) rather than "first 2 trading days of January" (window of 2).
Tested on equity (mechanism plausible: institutional window-dressing/light
volume) and crypto (falsification check: no month-end/holiday institutional
mechanism expected for a 24/7 market).

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
    entry_calendar_day: int = 20,
    exit_trading_day_jan: int = 1,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long from the close of the first trading day whose calendar day-of-month
    is strictly greater than `entry_calendar_day` in December, through the
    close of the `exit_trading_day_jan`'th trading day of the following
    January (inclusive); flat all other days.
    """
    df = _prep(price_df)
    idx = df.index

    years = idx.year
    months = idx.month
    days = idx.day

    pos = pd.Series(0, index=idx, dtype=int)

    dec_years = sorted(set(years[months == 12]))
    for y in dec_years:
        dec_mask = (years == y) & (months == 12) & (days > entry_calendar_day)
        dec_dates = idx[dec_mask]
        if len(dec_dates) == 0:
            continue
        entry_date = dec_dates[0]

        jan_mask = (years == y + 1) & (months == 1)
        jan_dates = idx[jan_mask]
        if len(jan_dates) < exit_trading_day_jan:
            # No January data yet (e.g. right at the end of the price
            # history) -- hold through to the end of available data.
            exit_date = idx[-1]
        else:
            exit_date = jan_dates[exit_trading_day_jan - 1]

        pos.loc[(idx >= entry_date) & (idx <= exit_date)] = 1

    return pos


def generate_returns(
    price_df: pd.DataFrame,
    entry_calendar_day: int = 20,
    exit_trading_day_jan: int = 1,
) -> pd.Series:
    """Daily strategy returns, position lagged by 1 day to avoid look-ahead."""
    df = _prep(price_df)
    pos = generate_signals(
        df,
        entry_calendar_day=entry_calendar_day,
        exit_trading_day_jan=exit_trading_day_jan,
    )
    price_col = "close" if "close" in df.columns else df.columns[0]
    daily_ret = df[price_col].pct_change()
    strat_ret = pos.shift(1).fillna(0) * daily_ret
    return strat_ret.fillna(0.0)
