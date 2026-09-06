"""Strategy: Turn-of-the-Month (ToM) calendar seasonality.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Lakonishok & Smidt (1988) documented that virtually all of the long-run
positive excess return in broad equity indexes (DJIA historically, SPY/QQQ
today) accrues during a narrow ~4-8 trading-day window straddling the
calendar month boundary: from a few trading days before month-end through
the first few trading days of the new month. Per Quantpedia's summary of
this literature, a simple actionable rule is: go long ``entry_days_before_
month_end`` trading days before the last trading day of the month, and exit
``exit_days_into_month`` trading days into the new month (holding through
month-end). Outside that window, stay flat. This is a pure calendar-time
signal -- no price/volume indicator involved, distinct from every other
strategy in this repo's index (all of which are technical-indicator-based).

Economic rationale (per the sources): monthly payroll/pension/401k
contribution flows and institutional rebalancing cycles concentrate fresh
buying pressure at each month's turn; this is not explained by risk
(volatility is not elevated in this window) and persists across ~30
national equity markets historically, though modern arbitrage may have
eroded/shifted the exact edge since the original 1988 paper.

Signal logic
------------
- Identify each month's trading-day calendar from the price index itself
  (trading days present in price_df, not a generic calendar -- handles
  holidays/weekends automatically since we only see actual bars).
- Entry: ``entry_days_before_month_end`` trading days before the LAST
  trading day of the current month (inclusive of that day itself when
  entry_days_before_month_end=0).
- Exit: at the close of the ``exit_days_into_month``'th trading day of the
  FOLLOWING month (1-indexed; exit_days_into_month=3 means exit at the
  close of the 3rd trading day of the new month, matching Quantpedia's
  literal rule).
- Flat at all other times. No indicator, no stop-loss -- pure calendar
  gating, so `generate_signals`/`generate_returns` take only date-window
  parameters as kwargs.

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


def generate_signals(
    price_df: pd.DataFrame,
    entry_days_before_month_end: int = 1,
    exit_days_into_month: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series driven purely by calendar
    position within each month, using the ACTUAL trading days present in
    price_df's index (so holidays/weekends are naturally skipped)."""
    df = _prep(price_df)
    idx = df.index

    # Group trading days by (year, month) using the actual index.
    ym = pd.Series(idx).dt.to_period("M")
    position = pd.Series(0, index=idx, dtype=int)

    # Map each (year,month) period -> list of positions (integer locations)
    # of its trading days within idx, in order.
    groups: dict = {}
    for i, period in enumerate(ym):
        groups.setdefault(period, []).append(i)

    sorted_periods = sorted(groups.keys())

    for pi, period in enumerate(sorted_periods):
        days_this_month = groups[period]
        n = len(days_this_month)
        # Entry index: entry_days_before_month_end days before the LAST
        # trading day of this month (0 = the last day itself).
        entry_offset = entry_days_before_month_end
        if entry_offset >= n:
            continue
        entry_loc = days_this_month[n - 1 - entry_offset]

        # Exit index: the exit_days_into_month'th trading day of the NEXT
        # month (1-indexed). If there's no next month in the data, hold to
        # the end of the available series (can't look into the future).
        if pi + 1 < len(sorted_periods):
            next_days = groups[sorted_periods[pi + 1]]
            exit_pos = exit_days_into_month - 1  # 0-indexed
            if exit_pos < len(next_days):
                exit_loc = next_days[exit_pos]
            else:
                exit_loc = next_days[-1]
        else:
            exit_loc = len(idx) - 1  # ran off the end of data

        if exit_loc < entry_loc:
            continue
        position.iloc[entry_loc:exit_loc + 1] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    entry_days_before_month_end: int = 1,
    exit_days_into_month: int = 3,
) -> pd.Series:
    """Daily strategy returns: position (from generate_signals, using
    yesterday's close-of-day decision applied to today's return, i.e. we
    enter/exit AT THE CLOSE of the signal day and hold through the next
    day's return) times the underlying daily simple return."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        entry_days_before_month_end=entry_days_before_month_end,
        exit_days_into_month=exit_days_into_month,
    )
    # Shift position by 1 so today's return is only earned if we were
    # already in position as of yesterday's close (avoid lookahead).
    strat_returns = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_returns
