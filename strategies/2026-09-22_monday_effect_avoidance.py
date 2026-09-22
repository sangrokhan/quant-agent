"""Strategy: Monday Effect avoidance (skip Monday's return, stay long other weekdays).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-069):
Per the Monday Effect / Weekend Effect literature (Cross 1973; Keef 2009,
ScienceDirect "The dynamics of the Monday effect in international stock
markets"; Linton 2006 FMG working paper; GRITTI 2024 "The Calendar Effects
in Financial Markets" thesis; Investopedia, all cited on the Google SERP
for the search query, read via browser_exec since `web_search`'s DDGS
backend intermittently TLS-errors), Monday stock returns are, on average,
statistically lower than -- and often negative versus -- returns on other
weekdays, a long-documented anomaly (Frank Cross first documented it in
1973; Keef 2009 confirms "the average return on Mondays is statistically
less than zero" across multiple international markets). GRITTI's thesis
describes the classic derived strategy as avoiding exposure over the
Friday-close-to-Monday-close gap. Implemented here as the simplest directly
testable variant: skip being long specifically ON Mondays (i.e. the
position built up by prior close is not held into Monday's own trading
session -- flat during Monday, long the rest of the week), since the
literature's own finding is that Monday's return specifically (not just
the weekend gap) is the systematically weak day. First
Monday-Effect/day-of-week strategy in this repo (0 prior KB hits).

Signal logic
------------
- Purely calendar-driven, no price-derived indicator. Long whenever the
  bar's day-of-week is Tuesday, Wednesday, Thursday, or Friday. Flat
  whenever the bar's day-of-week is Monday (or when included, other
  optionally-avoided days, configurable via avoid_weekdays).
- No time-stop needed -- flips daily purely off the calendar.
- Flat on avoided days. Long-only (no short per SAFETY.md scope) on other
  days.

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
    avoid_weekdays: tuple = (0,),  # 0=Monday, 1=Tuesday, ..., 6=Sunday (pandas dayofweek convention)
) -> pd.Series:
    df = _prep(price_df)
    idx = df.index
    dow = idx.tz_localize(None).dayofweek if idx.tz is not None else idx.dayofweek

    avoided = pd.Series(dow, index=idx).isin(list(avoid_weekdays))
    position = pd.Series((~avoided).astype(int), index=idx)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    avoid_weekdays: tuple = (0,),
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(df, avoid_weekdays=avoid_weekdays)
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
