"""Strategy: Options-Expiration-Week (OPEX) seasonal long-only strategy.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-149):
US equities exhibit above-average returns during the week containing the
monthly options-expiration Friday (the Friday before the 3rd Saturday of
each month), driven by dealer gamma-hedging/open-interest unwind dynamics
into expiration. Per QuantifiedStrategies.com ("The Options Expiration Week
Effect | OPEX Seasonality"): a simple test of buying at the Monday open of
OPEX week and selling at the Friday (expiration day) close produced a
positive CAGR while being invested only ~18% of the time; April tends to be
the strongest month, July/January the weakest. This is a purely
calendar-based seasonal strategy applied here to daily bars (enter at the
Monday close of OPEX week -- using close-to-close since we only have daily
OHLC and shift(1) exposure like every other strategy in this repo -- hold
through Friday's close).

Signal logic
------------
- For each month, the "OPEX Friday" is the 3rd Friday of the month
  (Friday before the 3rd Saturday).
- "OPEX week" = the Monday-Friday calendar week containing that Friday.
- Long (position=1) on every trading day that falls within OPEX week
  (from the first trading day of that week through OPEX Friday inclusive).
- Flat otherwise.
- No stop-loss/target -- purely calendar-timed, matching the source's own
  simple test.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _opex_friday(year: int, month: int, tz=None) -> pd.Timestamp:
    """3rd Friday of the given year/month (Friday before the 3rd Saturday)."""
    first = pd.Timestamp(year=year, month=month, day=1, tz=tz)
    # weekday(): Monday=0 ... Friday=4
    first_friday_offset = (4 - first.weekday()) % 7
    first_friday = first + pd.Timedelta(days=first_friday_offset)
    third_friday = first_friday + pd.Timedelta(days=14)
    return third_friday


def generate_signals(
    price_df: pd.DataFrame,
    entry_day_offset: int = 0,
    exit_on_opex_friday: bool = True,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    ``entry_day_offset``: 0 = enter Monday of OPEX week (default per source);
        e.g. 2 = enter Wednesday of OPEX week (a tighter/later-entry variant
        for parameter sensitivity testing).
    ``exit_on_opex_friday``: if True, hold through OPEX Friday's close only;
        if False, hold through the rest of that calendar week too (in case
        OPEX Friday is a market holiday and trading continues).
    """
    df = _prep(price_df)
    idx = df.index
    tz = getattr(idx, "tz", None)

    position = pd.Series(0, index=idx, dtype=int)

    months = sorted(set((ts.year, ts.month) for ts in idx))
    # Also consider the month before/after to catch week-boundary spillover.
    extra_months = set()
    for y, m in months:
        prev_m = 12 if m == 1 else m - 1
        prev_y = y - 1 if m == 1 else y
        next_m = 1 if m == 12 else m + 1
        next_y = y + 1 if m == 12 else y
        extra_months.add((prev_y, prev_m))
        extra_months.add((next_y, next_m))
    all_months = sorted(set(months) | extra_months)

    for y, m in all_months:
        opex_fri = _opex_friday(y, m, tz=tz)
        week_monday = opex_fri - pd.Timedelta(days=opex_fri.weekday())  # Monday of that week
        entry_date = week_monday + pd.Timedelta(days=entry_day_offset)
        exit_date = opex_fri if exit_on_opex_friday else week_monday + pd.Timedelta(days=4)

        mask = (idx >= entry_date) & (idx <= exit_date)
        position.loc[mask] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # Shift by 1 day to avoid look-ahead: yesterday's signal drives today's return.
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
