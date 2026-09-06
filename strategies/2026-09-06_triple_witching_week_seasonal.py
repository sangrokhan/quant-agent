"""Strategy: Triple Witching week seasonal effect (long Monday open, exit Thursday close).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-178):
"Triple witching" is the quarterly simultaneous expiration of stock options,
stock index options, and stock index futures on the third Friday of March,
June, September, and December. Per BigPic Solutions' own backtested rule
(Google SERP snippet -- source page itself 404'd, but the exact numeric rule
was fully disclosed in the snippet): "Go long Monday open of witching week,
exit Thursday close. Average gain: +0.55% per trade, 65% win rate across 128
backtested trades." The economic rationale (elsewhere corroborated by
Investopedia/Interactive Brokers/Nasdaq explainers of triple witching) is
that dealer/market-maker gamma-hedging flows and elevated volume/rebalancing
activity into the simultaneous expiration create a systematic pre-expiration
drift, distinct from this repo's already-tested OPEX-week strategy
(2026-09-06-149, which uses the MONTHLY 3rd-Friday options expiration every
month) -- triple witching is the QUARTERLY subset where index futures ALSO
expire simultaneously, a structurally different (larger, less frequent)
event with its own documented effect.

Signal logic
------------
- Identify each calendar quarter's 3rd Friday of March/June/September/
  December (the triple-witching date).
- Entry: at the close of the Monday of that week (i.e. position opens
  Tuesday via the standard T+1 shift-based return convention used
  throughout this repo -- "enter Monday's open" is approximated as
  "signal=1 starting Monday's close" so the position captures Tuesday's
  return onward, consistent with generate_returns' fixed shift(1) daily-bar
  convention).
- Exit: at the close of the Thursday of that same week.
- Flat all other days.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series {0,1} long/flat
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _third_friday(year: int, month: int) -> pd.Timestamp:
    """Return the third Friday of the given year/month."""
    first = pd.Timestamp(year=year, month=month, day=1)
    # weekday(): Monday=0 ... Friday=4
    days_to_friday = (4 - first.weekday()) % 7
    first_friday = first + pd.Timedelta(days=days_to_friday)
    return first_friday + pd.Timedelta(weeks=2)


def _witching_week_windows(idx: pd.DatetimeIndex):
    """Yield (monday, thursday) pairs for each quarter's witching week
    spanning the index's year range."""
    tz = getattr(idx, "tz", None)
    years = range(idx.min().year - 1, idx.max().year + 2)
    for year in years:
        for month in (3, 6, 9, 12):
            friday = _third_friday(year, month)
            monday = friday - pd.Timedelta(days=4)
            thursday = friday - pd.Timedelta(days=1)
            if tz is not None:
                monday = monday.tz_localize(tz)
                thursday = thursday.tz_localize(tz)
            yield monday, thursday


def generate_signals(
    price_df: pd.DataFrame,
    entry_weekday_offset: int = 0,  # 0 = Monday of witching week
    exit_weekday_offset: int = 3,  # 3 = Thursday of witching week
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    idx = close.index

    position = pd.Series(0, index=idx, dtype=int)

    for monday, thursday in _witching_week_windows(idx):
        entry_date = monday + pd.Timedelta(days=entry_weekday_offset)
        exit_date = monday + pd.Timedelta(days=exit_weekday_offset)
        mask = (idx >= entry_date) & (idx <= exit_date)
        position.loc[mask] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
