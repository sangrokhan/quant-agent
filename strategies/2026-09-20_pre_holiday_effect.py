"""Strategy: Pre-Holiday Effect -- long the last trading day before a market holiday.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-061):
Per Investing.com's "Using The Pre-Holiday Effect As An Effective Trading
Strategy" (https://www.investing.com/analysis/pre-holiday-effect-200169596,
visited this iteration via browser_exec fallback -- web_search DDGS
backend hit repeated TLS/connection-reset errors this iteration), which
cites the academic literature directly (Lakonishok & Smidt, published in
The Journal of Finance): "On the trading day prior to holidays, stocks
advance with disproportionate frequency and show high mean returns
averaging nine to fourteen times the mean return for the remaining days
of the year. Over one third of the total return accruing to the market
portfolio over the 1963-1982 period was earned on the eight trading days
which each year fall before holiday market closings."

Mechanical rule: identify the last trading day before each U.S. market
holiday (detected purely from the OHLCV data's own trading-day calendar,
without an external holiday-calendar dependency: a trading day is a
"pre-holiday" day if the gap in calendar days to the NEXT trading day
exceeds the normal weekly gap for that weekday -- i.e. 1 day for
Mon-Thu, 3 days for Friday -- since a market holiday inserts an extra
non-trading calendar day beyond the ordinary weekend pattern). Long that
day's close-to-next-trading-day-close return only, flat all other days.

First Pre-Holiday-Effect strategy in this repo (0 prior "Pre Holiday"
entries in strategies_index.jsonl); distinct from all other calendar-
anomaly entries (Turnaround Tuesday, Turn-of-Month, Santa Claus,
Quad Witching, Sell-in-May, day-of-week effects) which key off weekday or
date-of-month/date-of-year triggers, not a data-inferred holiday-calendar
gap detection.

Source: https://www.investing.com/analysis/pre-holiday-effect-200169596
(secondary source citing the primary academic study directly by name and
quote; the effect and its magnitude are disclosed, not paywalled).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (position: 1 long/0 flat)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(price_df: pd.DataFrame) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long on the last trading day before a detected market holiday (i.e.
    the day whose position size will be applied to the NEXT day's return
    via generate_returns' position.shift(1) convention).
    """
    df = _prep(price_df)
    idx = df.index

    position = pd.Series(0, index=idx, dtype=int)
    for i in range(len(idx) - 1):
        today = idx[i]
        next_day = idx[i + 1]
        gap_days = (next_day - today).days
        normal_gap = 3 if today.weekday() == 4 else 1  # Friday -> Monday is normally 3
        if gap_days > normal_gap:
            position.iloc[i] = 1
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
