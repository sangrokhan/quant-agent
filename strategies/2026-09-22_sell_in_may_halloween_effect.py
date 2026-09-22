"""Strategy: Sell-in-May / Halloween Effect seasonal calendar (Nov-Apr long, flat May-Oct).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-067):
Per the "Sell in May and Go Away" / Halloween Effect literature (Bouman &
Jacobsen 2002, "The Halloween Indicator, 'Sell in May and Go Away'",
American Economic Review; corroborated by Guo et al. 2014 and a 2018
follow-up study covering 65 developed/emerging markets, all cited on the
Google SERP for "Sell in May Halloween indicator strategy specific trading
rule November April", read via browser_exec since `web_search`'s DDGS
backend intermittently TLS-errors), average 6-month stock returns are
roughly 4% higher during November-April than during May-October, a robust
and long-studied calendar anomaly persisting across most global equity
markets studied. Disclosed rule (Investopedia, Moomoo, CFI, all
consistent): "buy stocks in November, hold them through the winter months,
and sell them in April" -- i.e. long Nov 1 through Apr 30, flat May 1
through Oct 31. First "Sell in May"/Halloween-effect strategy in this repo
(0 prior KB hits).

Signal logic
------------
- Purely calendar-driven, no price-derived indicator. Long whenever the
  bar's calendar month is in {Nov, Dec, Jan, Feb, Mar, Apr} (i.e. month is
  11, 12, 1, 2, 3, or 4). Flat whenever the month is in {May, Jun, Jul,
  Aug, Sep, Oct} (5-10).
- No time-stop needed -- position changes exactly at the two calendar
  boundaries (Apr->May flat, Oct->Nov long) each year.
- Flat during the "sell" half. Long-only (no short per SAFETY.md scope)
  during the "buy" half.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
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


def generate_signals(
    price_df: pd.DataFrame,
    long_start_month: int = 11,
    long_end_month: int = 4,
) -> pd.Series:
    df = _prep(price_df)
    idx = df.index
    months = idx.tz_localize(None).month if idx.tz is not None else idx.month

    if long_start_month > long_end_month:
        # wraps around year end, e.g. Nov(11) -> Apr(4)
        in_long_window = (months >= long_start_month) | (months <= long_end_month)
    else:
        in_long_window = (months >= long_start_month) & (months <= long_end_month)

    position = pd.Series(in_long_window.astype(int), index=idx)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    long_start_month: int = 11,
    long_end_month: int = 4,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(df, long_start_month=long_start_month, long_end_month=long_end_month)
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
