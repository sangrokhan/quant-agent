"""Strategy: JETS (airline-sector ETF) pre/post U.S.-federal-holiday
calendar-anomaly window, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-19-001),
sourced from Quantpedia's "Do Airline Stocks Take Off Around U.S.
Holidays?" blog post (18 Sep 2026,
https://quantpedia.com/do-airline-stocks-take-off-around-u-s-holidays/,
read via browser_exec Quantpedia blog listing -> article page). The
article studies the U.S. Global Jets ETF (JETS) around the 8-9 major U.S.
federal holidays (New Year's, MLK, Presidents' Day, Memorial Day, July 4,
Labor Day, Thanksgiving, Christmas, plus Juneteenth from 2022) and finds a
positive average-return drift concentrated in the four trading days before
each holiday (D-4 through D-1), plus a further-extended window running
through D+8, driven by anticipated holiday-travel demand for airlines
specifically (an airline-sector analog to the article's earlier
crude-oil/gasoline pre-holiday-travel finding, which this repo already
tested for pre_holiday_effect.py -- but that prior entry used a
generic index-gap detector on ANY >=3-day gap, i.e. ordinary weekends too,
not specifically federal holidays, and was not airline-sector-specific).

This implementation:
  1. Uses `pandas.tseries.holiday.USFederalHolidayCalendar` (+ Juneteenth
     added manually from 2022 onward) to get the EXACT holiday calendar
     the source studied, rather than a generic calendar-gap heuristic.
  2. For each holiday date D, finds the position of the last trading day
     strictly before D (= "D-1" in the source's notation) within the
     price series' own index.
  3. Exposes two of the source's three strategies as one parameterized
     rule (the third, the JETS-USO cross-asset spread, needs simultaneous
     two-symbol data and is infeasible under this repo's single-symbol
     generate_returns(price_df, **params) contract, so it is not
     implemented here):
       - "D-4_to_D-1" (source's short pre-holiday-only window): entry at
         close of D-(entry_days_before), exit at close of D-1.
       - "D-4_to_D+8" (source's longer window straddling the holiday):
         entry at close of D-(entry_days_before), exit at close of
         D+exit_days_after.
     Controlled by a single `exit_days_after` param: negative values exit
     before the holiday (e.g. -1 == D-1), positive values exit after
     (e.g. +8 == D+8).
  4. Tested here primarily on JETS (equity) plus QQQ/SPY as a
     falsification check (the mechanism is airline-travel-specific, so a
     broad index ETF should NOT show the same edge) and on crypto pairs
     as a second falsification check (24/7 markets have no holiday
     closures at all, so the holiday-calendar signal is structurally
     inert there -- position stays flat almost everywhere).

Interface contract for validators (see validation/validators.py) and grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day relative to the *signal decision* -- the
        decision to buy at D-entry_days_before's close is itself based only
        on the known-in-advance federal holiday calendar, so no future
        price information leaks into the signal; the .shift(1) below still
        applies conservatively so day-of the entry/exit bar's OWN return
        is captured starting the next bar, matching every other strategy
        in this repo's convention).
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _us_holidays(start, end) -> pd.DatetimeIndex:
    cal = USFederalHolidayCalendar()
    holidays = cal.holidays(start=start, end=end)
    # Juneteenth became a federal holiday in 2021 (observed federally from
    # 2022 onward) but USFederalHolidayCalendar (pandas built-in) does not
    # include it -- add June 19th (or nearest weekday if it falls on a
    # weekend) for each year from 2022 onward, matching the source's
    # 9-holiday calendar from 2022.
    juneteenths = []
    for year in range(2022, end.year + 2):
        d = pd.Timestamp(year=year, month=6, day=19)
        if d.weekday() == 5:  # Saturday -> observed Friday
            d = d - pd.Timedelta(days=1)
        elif d.weekday() == 6:  # Sunday -> observed Monday
            d = d + pd.Timedelta(days=1)
        juneteenths.append(d)
    all_holidays = holidays.union(pd.DatetimeIndex(juneteenths))
    return all_holidays[(all_holidays >= pd.Timestamp(start)) & (all_holidays <= pd.Timestamp(end))]


def generate_signals(
    price_df: pd.DataFrame,
    entry_days_before: int = 5,
    exit_days_after: int = -1,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    entry_days_before: how many trading days before the holiday to BUY at
        that day's close (source's "D-5" = entry_days_before=5 for the
        D-4..D-1 window's entry).
    exit_days_after: SELL at close of the day this many trading days after
        the holiday if positive (e.g. +8 == D+8), or if negative, sell at
        close of the day |exit_days_after| trading days before the holiday
        (e.g. -1 == D-1, the source's short window's exit).
    """
    df = _prep(price_df)
    idx = df.index
    n = len(idx)
    position = np.zeros(n, dtype=int)
    if n < 3:
        return pd.Series(position, index=idx)

    # Normalize to naive dates for holiday-calendar comparison (index may
    # be tz-aware UTC from the loader).
    idx_dates = pd.DatetimeIndex([pd.Timestamp(d).tz_localize(None) for d in idx])

    holidays = _us_holidays(idx_dates.min(), idx_dates.max())

    for h in holidays:
        # position of the last trading day strictly before the holiday
        pos_d_minus_1 = idx_dates.searchsorted(h, side="left") - 1
        if pos_d_minus_1 < 0:
            continue

        entry_pos = pos_d_minus_1 - (entry_days_before - 1)
        if exit_days_after > 0:
            exit_pos = pos_d_minus_1 + exit_days_after
        else:
            exit_pos = pos_d_minus_1 - (abs(exit_days_after) - 1)

        entry_pos = max(entry_pos, -1)
        exit_pos = min(exit_pos, n - 1)
        if exit_pos <= entry_pos:
            continue

        # Held on trading days (entry_pos, exit_pos] inclusive of exit_pos,
        # exclusive of entry_pos (bought AT entry_pos's close, so entry_pos
        # itself is not "held" for that day; holds start the next bar).
        lo = max(entry_pos + 1, 0)
        hi = exit_pos + 1  # slice end exclusive
        position[lo:hi] = 1

    return pd.Series(position, index=idx)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
