"""Strategy: Turn-of-the-Month (TOM) equity calendar-day seasonality.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-124):
Source: Google AI-overview synthesis of ScienceDirect/QuantPedia/Forbes
coverage of the well-documented Turn-of-the-Month equity anomaly. The
classic rule: enter long at the close of the entry_days_before_month_end-
th-to-last trading day of the current month, exit at the close of the
exit_days_into_month-th trading day of the new month -- roughly a 4-7
trading-day hold each month, flat/cash the rest of the time. Explained by
month-end institutional cash flows (payroll deposits, pension fund
rebalancing, monthly mortgage/investment contributions) creating
automatic buying pressure concentrated around month boundaries.

Distinct from the previously-tested Day-of-Week (Monday/Friday) seasonality
(2026-09-08-096, a day-of-WEEK effect) -- this is a day-of-MONTH /
calendar-position effect. First Turn-of-Month strategy in this repo.

Mechanical rule implemented
----------------------------
- Within each calendar month, rank trading days from the end (0 = last
  trading day of month, 1 = second-to-last, ...) and from the start of the
  following month (0 = first trading day, 1 = second, ...).
- Long position active from entry_days_before_month_end-th-to-last trading
  day of the current month through exit_days_into_month-th trading day of
  the NEXT month (inclusive), flat otherwise.
- No indicator/parameter besides the two calendar offsets -- pure calendar
  anomaly, long-only, no trend filter (matches source's own
  unconditional-seasonal framing).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (position: {0,1})
    generate_returns(price_df, **params) -> pd.Series
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
    entry_days_before_month_end: int = 4,  # 5th-to-last trading day (0-indexed offset 4)
    exit_days_into_month: int = 2,  # 3rd trading day of new month (0-indexed offset 2)
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    idx = df.index

    ym = pd.Series(idx.year * 100 + idx.month, index=idx)

    # Rank trading days within each month, from the start (0-indexed) and
    # from the end (0-indexed, 0 = last day of that month).
    rank_from_start = ym.groupby(ym).cumcount()
    rank_from_end = ym.groupby(ym).cumcount(ascending=False)

    near_month_end = rank_from_end <= entry_days_before_month_end
    near_month_start = rank_from_start <= exit_days_into_month

    position = (near_month_end | near_month_start).astype(int)
    position.index = idx
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
