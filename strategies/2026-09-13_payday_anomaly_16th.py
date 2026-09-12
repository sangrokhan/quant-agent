"""Strategy: Payday Anomaly (Ma & Pratt, SSRN 3257064, via Quantpedia
https://quantpedia.com/strategies/payday-anomaly/).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Employees are commonly paid semi-monthly (15th and end-of-month). A portion
of each paycheck's retirement contribution reaches financial institutions
and gets invested in broad-market funds (e.g. S&P 500) the following
business day. Since the end-of-month paycheck effect is already captured by
the well-known turn-of-the-month anomaly (extensively tested elsewhere in
this repo), this strategy targets the OTHER semi-monthly paycheck: the
mid-month cycle. Quantpedia's own summary of the source paper finds the
16th CALENDAR day of the month (the trading day following the 15th payday)
is the 3rd-best day of the month for S&P 500 returns.

This is mechanically DISTINCT from every prior turn-of-month/intramonth
strategy tested in this repo (2026-09-06-169, 2026-09-11-124/125,
2026-09-08-139/142, 2026-09-13-022), all of which anchor to TRADING-DAY
counts from the front/back of the month (a pure trading-calendar
construction). This strategy instead anchors to a specific CALENDAR-day
mid-month window (around the 15th/16th), a genuinely different mechanism
tied to actual payroll dates rather than trading-day position.

Signal logic
------------
- window_start_day / window_end_day: calendar-day-of-month bounds (source's
  own single-day rule is window_start_day=16, window_end_day=16; the
  strategy also supports testing a small window, e.g. 15-17, since actual
  paycheck-clearing timing can vary +/- a business day around holidays/
  weekends).
- On each bar whose calendar day-of-month falls within
  [window_start_day, window_end_day] (inclusive), go long; flat otherwise
  (single-day or short multi-day hold each month, unconditional -- no
  momentum/trend gate, matching the source's own "simply buy and hold"
  rule).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
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
    window_start_day: int = 16,
    window_end_day: int = 16,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    idx = df.index

    day_of_month = pd.Series(idx.day, index=idx)
    long_mask = (day_of_month >= window_start_day) & (day_of_month <= window_end_day)

    position = long_mask.astype(int)
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
