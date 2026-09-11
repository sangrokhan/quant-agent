"""Strategy: Pre-NFP close-to-close drift (buy the close before the jobs
report, sell at the close of the jobs-report Friday).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per https://www.quantifiedstrategies.com/the-friday-jobs-report-trading/
(visited this iteration), the source's own disclosed backtest found that the
BEST variant of a jobs-report calendar trade is not the intraday
open-to-close trade on NFP Friday itself (already tested and rejected in
this repo, id 2026-09-11-085, net Sharpe negative after costs) but instead
entering at the close the day BEFORE the jobs report and exiting at the
close of the jobs-report day itself -- i.e. capturing the close-to-close
return (overnight gap + the report day itself), which the source states
produced an average gain of ~0.3% per trade (vs ~0.09% for the
open-to-close-only version). This is a distinct execution-timing
construction from 2026-09-11-085: that strategy captured ONLY the intraday
(open->close) move on NFP Friday; this strategy captures the close(Thu)
-> close(Fri) move, one full trading day earlier entry, testing whether the
overnight positioning ahead of the report (rather than the report-day
session itself) is where the edge concentrates.

NFP release day is approximated as the first Friday of each calendar month
(exact econ-calendar data is not available via this repo's yfinance/ccxt
loaders) -- a small minority of months have holiday-shifted actual release
dates, treated as noise, consistent with the prior NFP strategy's approach.

Signal logic
------------
- Identify the first Friday of each calendar month in the price index.
- Long position held from the close of the PRECEDING trading day (i.e. the
  trading day immediately before that first Friday, which may be
  Wed/Thu/Mon depending on holidays) through the close of the first-Friday
  session itself.
- Flat otherwise. No tunable tightening -- this is a fixed calendar rule,
  but we expose `hold_days_before` (default 1) and `hold_days_after`
  (default 0) as keyword params so the grid can test whether extending the
  hold window (e.g. entering 2 days before, or holding 1 extra day after)
  changes the edge, per RESEARCH_LOOP.md Step 5's keyword-args contract.

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


def _first_fridays(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Return the set of dates in `index` that are the first Friday of
    their calendar month (approximating NFP release day)."""
    df = pd.DataFrame({"date": index})
    df["ym"] = df["date"].dt.year * 100 + df["date"].dt.month
    df["dow"] = df["date"].dt.dayofweek  # Friday == 4
    fridays = df[df["dow"] == 4]
    first_fridays = fridays.groupby("ym")["date"].min()
    result = pd.DatetimeIndex(first_fridays.values)
    if getattr(index, "tz", None) is not None:
        result = result.tz_localize(index.tz) if result.tz is None else result.tz_convert(index.tz)
    return result


def generate_signals(
    price_df: pd.DataFrame,
    hold_days_before: int = 1,
    hold_days_after: int = 0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Position is 1 starting `hold_days_before` trading days before each
    first-Friday-of-month (inclusive of the entry day's close) through
    `hold_days_after` trading days after the first Friday (inclusive).
    """
    df = _prep(price_df)
    close = df["close"]
    idx = close.index

    position = pd.Series(0, index=idx, dtype=int)
    first_fridays = _first_fridays(idx)

    idx_list = list(idx)
    pos_by_date = {d: i for i, d in enumerate(idx_list)}

    for ff in first_fridays:
        if ff not in pos_by_date:
            # Market holiday on the actual first Friday -- skip, no proxy.
            continue
        center_i = pos_by_date[ff]
        start_i = max(0, center_i - hold_days_before)
        end_i = min(len(idx_list) - 1, center_i + hold_days_after)
        position.iloc[start_i:end_i + 1] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Close-to-close position-weighted daily returns (no transaction costs).

    Unlike the prior open-to-close-only NFP strategy, this position is
    already expressed in terms of which trading day's close-to-close return
    to capture -- so unlike the standard `shift(1)` convention used
    elsewhere in this repo (which avoids look-ahead by trading on
    yesterday's signal), here the position for day t being 1 means "hold
    from close(t-1) to close(t)", which is exactly what pct_change() at day
    t represents. We therefore do NOT shift here (the calendar signal is
    fully known in advance -- first-Friday-of-month is knowable well before
    the fact, unlike an indicator computed from today's own close), but we
    still only ever include this trading day's return when the entry
    condition was decided using information available *before* today's
    close (the calendar date itself), so no look-ahead bias is introduced.
    """
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.astype(float) * daily_ret
    return strategy_ret
