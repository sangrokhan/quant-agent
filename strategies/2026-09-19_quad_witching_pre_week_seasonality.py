"""Strategy: Quadruple-Witching calendar seasonality (pre-witching-week long,
post-witching-week flat/avoid).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-19-053):
Per QuantifiedStrategies.com's "Quad Witching Day - Bullish or Bearish?
(Quadruple Witching Backtest)"
(https://www.quantifiedstrategies.com/quadruple-witching/), quadruple
witching (the simultaneous quarterly expiration of stock-index futures,
stock-index options, single-stock options, and single-stock futures, on
the 3rd Friday of March/June/September/December) shows a specific
disclosed seasonal pattern: (a) the WEEK LEADING UP TO quad witching
(bullish, strong positive returns), (b) the quad-witching DAY itself
(bearish/below-average), and (c) the WEEK AFTER quad witching (negative
returns, "particularly poor in June and September"). This is a purely
calendar-based seasonality distinct from every other calendar-effect
strategy already tested in this repo (Turnaround Tuesday, Turn-of-Month,
OPEX week, day-of-week effects, presidential cycle, Santa Claus rally,
Sell-in-May) -- none of them key off the specific quarterly 3rd-Friday
derivatives-expiration date.

We test the two disclosed legs as a single combined position: LONG during
the `pre_days`-trading-day window immediately before a quad-witching
Friday (capturing the disclosed bullish pre-witching-week effect), FLAT on
quad-witching day itself and during the `post_days`-trading-day window
immediately after (avoiding the disclosed bearish day + negative
post-witching week), and FLAT at all other times (this is a purely
seasonal/event-driven strategy, not a standing trend-follow).

Quad-witching Fridays are computed directly from the calendar (3rd Friday
of March/June/September/December) -- no external data or lookup table
needed, matching the source's own "count Fridays in the month" approach.
Distances are measured in TRADING DAYS (positions in price_df's own
DatetimeIndex), not calendar days, so it works correctly across weekends/
holidays for whatever asset's own trading calendar is supplied.

Signal logic
------------
- Build the list of quad-witching Fridays (3rd Friday of Mar/Jun/Sep/Dec)
  covering price_df's date range (with padding).
- For each quad-witching date qw, find its integer position in price_df's
  own trading-day index (nearest available trading day, e.g. the equity
  calendar naturally skips weekends/holidays; for crypto's continuous
  calendar it's an exact hit almost always).
- position[i] = 1 if i is within `pre_days` trading days BEFORE (and not
  equal to) a witching day's index position, i.e.
  witching_pos - pre_days <= i < witching_pos.
- position[i] = 0 if i is within `post_days` trading days AFTER (and
  including) a witching day's index position, i.e.
  witching_pos <= i <= witching_pos + post_days (this explicit flat
  overrides any competing pre-window from the NEXT quarter's witching
  date, since post-window is checked after pre-window and always wins for
  overlapping days -- in practice pre_days/post_days are small (~5) so
  overlap across different quarters' witching dates never occurs).
- position[i] = 0 otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def _third_friday(year: int, month: int) -> pd.Timestamp:
    """Return the 3rd Friday of the given year/month (UTC tz-aware)."""
    d = pd.Timestamp(year=year, month=month, day=1, tz="UTC")
    first_friday_offset = (4 - d.weekday()) % 7  # Friday == weekday 4
    first_friday = d + pd.Timedelta(days=first_friday_offset)
    return first_friday + pd.Timedelta(weeks=2)


def _quad_witching_dates(start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    """All 3rd-Friday-of-{Mar,Jun,Sep,Dec} dates covering [start, end], with padding."""
    dates = []
    for year in range(start.year - 1, end.year + 2):
        for month in (3, 6, 9, 12):
            dates.append(_third_friday(year, month))
    return pd.DatetimeIndex(sorted(dates))


def generate_signals(
    price_df: pd.DataFrame,
    pre_days: int = 5,
    post_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    idx = df.index
    n = len(idx)
    position = np.zeros(n, dtype=int)

    qw_dates = _quad_witching_dates(idx.min(), idx.max())

    # For each quad-witching date, find the nearest trading-day position
    # in idx (searchsorted gives the insertion point -> nearest available
    # trading day at/after the witching Friday, which for equities lands
    # on the Friday itself in the vast majority of cases).
    witching_positions = np.searchsorted(idx.values, qw_dates.values)
    witching_positions = witching_positions[witching_positions < n]

    for wp in witching_positions:
        pre_start = max(0, wp - pre_days)
        position[pre_start:wp] = 1  # pre-witching window: long
        post_end = min(n, wp + post_days + 1)
        position[wp:post_end] = 0  # witching day + post window: flat (overrides)

    return pd.Series(position, index=idx, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    pre_days: int = 5,
    post_days: int = 5,
) -> pd.Series:
    """Return the strategy's daily return series."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(df, pre_days=pre_days, post_days=post_days)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
