"""Strategy: Pre-Holiday Effect in Commodities (USO/UGA D-5 -> D-1 hold).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-XXX):
Per Quantpedia's "Pre-Holiday Effect in Commodities" (Radovan Vojtko, Cyril
Dujava, https://quantpedia.com/pre-holiday-effect-in-commodities/, Oct
2024, read via browser_exec since web_extract's DDGS backend cannot
extract page content): crude oil (USO) and gasoline (UGA) ETFs show a
short-term price drift concentrated in the D-4 to D-1 window before major
US federal holidays (D = the holiday date), attributed to anticipated
holiday travel/fuel demand. Source's own disclosed exact rule:

    Enter: buy at close of D-5.
    Hold: D-4, D-3, D-2 (unchanged position).
    Exit: sell at close of D-1 (the last trading day before the holiday).

Source's own reported backtest (USO 2006-2024, UGA 2008-2024): both
profitable, UGA "almost doubled" USO's performance with slightly better
risk metrics; both saw a D+1 selloff/profit-taking (not traded here, exit
is strictly at D-1 close per source's own rule).

Distinct from every other holiday/pre-holiday strategy already in this
repo's knowledge base:
  - 2026-09-03-020 (generic ">=3-calendar-day trading-gap" heuristic,
    catches ordinary weekends too -- not this repo's exact US-federal-
    holiday calendar, and entered/exited on different days: the single
    session immediately before/after the gap, not a D-5..D-1 multi-day
    hold).
  - 2026-09-19-001/2026-09-22-113 (JETS airline-holiday effect, same exact
    D-5->D-1 calendar mechanism and source article family, but tests the
    AIRLINE-DEMAND side [JETS ETF], not the FUEL-DEMAND side [USO/UGA]).
None of the ~11 other USO-related entries in this repo test this specific
D-5->D-1 holiday-anchored calendar rule.

Signal logic
------------
- US federal holiday calendar (via pandas' USFederalHolidayCalendar,
  matching the source's 9-holiday definition: New Year's, MLK, Presidents',
  Memorial, Juneteenth [from 2022], Independence, Labor, Thanksgiving,
  Christmas).
- For each holiday date D: find the trading day that is `entry_days_before`
  (default 5) trading days before D (call it D-5), and the trading day
  that is 1 trading day before D (D-1).
- Position: long from the CLOSE of D-5 through the CLOSE of D-1 (i.e. the
  strategy's daily return series realizes close-to-close returns on D-4,
  D-3, D-2, and D-1 -- the D-5 close itself is the entry price, not a
  return day).
- Long-only, no leverage (SAFETY.md). Flat all other days.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1})
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _holiday_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    cal = USFederalHolidayCalendar()
    start = index.min() - pd.Timedelta(days=30)
    end = index.max() + pd.Timedelta(days=30)
    return cal.holidays(start=start, end=end)


def generate_signals(
    price_df: pd.DataFrame,
    entry_days_before: int = 5,
) -> pd.Series:
    """Return a {0,1} position series: 1 on trading days from D-5 (entry
    price day, held from its close) through D-1 (exit day) inclusive of
    the intervening D-4..D-2 hold days.
    """
    df = _prep(price_df)
    idx = df.index

    position = pd.Series(0, index=idx, dtype=int)
    trading_days = idx.normalize()

    holidays = _holiday_dates(idx)
    for h in holidays:
        # Find the trading-day position of the last trading day strictly
        # before the holiday (D-1), then walk back entry_days_before-1
        # more trading days to get D-5 (default).
        before = trading_days[trading_days < h]
        if len(before) < entry_days_before:
            continue
        d_minus_1_pos = trading_days.get_loc(before[-1]) if before[-1] in trading_days else None
        # Use integer positions relative to the full trading_days array.
        # Find position of before[-1] in the full index.
        pos_d1 = idx.get_indexer([before[-1]])[0]
        pos_entry = pos_d1 - (entry_days_before - 1)
        if pos_entry < 0:
            continue
        # Hold from entry day's close (position becomes 1 starting the
        # NEXT bar, i.e. D-4) through D-1's close (last day position=1).
        # position.iloc[pos_entry+1 : pos_d1+1] = 1 realizes D-4..D-1
        # close-to-close returns.
        lo = pos_entry + 1
        hi = pos_d1 + 1
        if lo < hi:
            position.iloc[lo:hi] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    entry_days_before: int = 5,
) -> pd.Series:
    """Close-to-close daily returns, active only on D-4..D-1 of each
    US federal holiday window (per generate_signals)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, entry_days_before=entry_days_before)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position * daily_ret
    return strategy_ret.fillna(0.0)
