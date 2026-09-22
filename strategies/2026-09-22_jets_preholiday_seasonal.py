"""Strategy: JETS (U.S. Global Jets ETF) pre-holiday seasonal hold.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per Quantpedia's "Do Airline Stocks Take Off Around U.S. Holidays?"
(https://quantpedia.com/do-airline-stocks-take-off-around-u-s-holidays/,
18 Sep 2026, read via browser_exec this iteration), airline-sector stocks
(proxied by the JETS ETF) show a seasonal return pattern in the days
surrounding the 9 major U.S. market holidays (New Year's, MLK Day,
Presidents' Day, Memorial Day, Juneteenth [from 2022], Independence Day,
Labor Day, Thanksgiving, Christmas), attributed to holiday-travel-driven
demand expectations (an extension of the source's own prior finding of a
pre-holiday effect in crude oil/gasoline). Source's own disclosed rule for
the strongest standalone window ("JETS D-4 to D-1"): buy JETS at the
close of D-5 (5 trading days before the holiday), hold through D-1 (the
last trading day before the holiday), sell at the close of D-1. Reported
backtest (2015-2026): CAGR 7.14%, annualized vol 9.40%, max drawdown
-14.61%, Sharpe 0.76.

This is a genuinely new strategy family in this repo -- 0 prior matches
for "JETS|airline" combined with a specific single-asset mechanical rule
(the repo's other calendar-anomaly entries are either broad pre-holiday
equity-index effects on SPY/QQQ, 2026-09-03-020, or a Bitcoin-specific
next-day holiday-return study, 2026-09-07-009; neither targets the
airline sector specifically or JETS as the underlying).

Signal logic
------------
- Holidays: the same 9 U.S. federal holidays Quantpedia uses, built from
  pandas' USFederalHolidayCalendar (Columbus Day and Veterans Day
  excluded to match the source's list exactly; Juneteenth only applies
  from 2022 onward per the source, which pandas' own rule already
  reflects via its "nearest_workday" observance starting from the
  holiday's 2021 federal recognition -- we additionally hard-filter any
  Juneteenth occurrence before 2022 to match the source precisely).
- For each holiday date H (a market-closed day), find D-1 = the last
  trading day before H, and D-5 = 5 trading days before H (i.e. the bar 4
  trading days before D-1). Enter (position=1) at D-5's close (i.e. the
  bar AFTER D-5, matching "buy at the close of D-5" -> exposed starting
  next bar), hold through D-1, flat otherwise. Implemented directly as a
  {0,1} position series covering the trading days [D-4 .. D-1] inclusive
  (4 trading days of holding, matching "D-4 to D-1"), entered at D-5's
  close per source.
- No parameters beyond the holding-window definition itself are strategy-
  tunable in the source; we expose `lookback_days` (default 5, days before
  the holiday to enter) and `hold_days` (default 4, number of trading days
  held) as the grid-testable knobs to see how sensitive the effect is to
  the exact window source picked.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series   ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
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


def _holiday_dates(start, end, tz=None) -> list:
    cal = USFederalHolidayCalendar()
    # Exclude Columbus Day and Veterans Day to match Quantpedia's 9-holiday list.
    excluded = {"Columbus Day", "Veterans Day"}
    rules = [r for r in cal.rules if r.name not in excluded]
    # dates() requires tz-naive bounds; strip tz for the query, re-attach after.
    start_naive = pd.Timestamp(start).tz_localize(None) if getattr(start, "tzinfo", None) else pd.Timestamp(start)
    end_naive = pd.Timestamp(end).tz_localize(None) if getattr(end, "tzinfo", None) else pd.Timestamp(end)
    holidays = []
    for r in rules:
        dates = r.dates(start_naive, end_naive)
        for d in dates:
            # Juneteenth only recognized as a federal holiday from 2021;
            # source applies it from 2022 onward.
            if r.name == "Juneteenth National Independence Day" and d.year < 2022:
                continue
            ts = pd.Timestamp(d)
            if tz is not None:
                ts = ts.tz_localize(tz)
            holidays.append(ts)
    return sorted(holidays)


def generate_signals(
    price_df: pd.DataFrame,
    lookback_days: int = 5,
    hold_days: int = 4,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    idx = df.index

    position = pd.Series(0, index=idx, dtype=int)
    if len(idx) == 0:
        return position

    holidays = _holiday_dates(
        idx.min() - pd.Timedelta(days=10),
        idx.max() + pd.Timedelta(days=10),
        tz=idx.tz,
    )

    for h in holidays:
        # Find the position of the first trading day on/after the holiday
        # (the holiday itself is a market-closed day, so the trading-day
        # index won't contain it -- searchsorted finds D+0, i.e. the first
        # bar after the gap).
        pos_after = idx.searchsorted(h)
        if pos_after <= 0 or pos_after >= len(idx):
            continue
        d_minus_1 = pos_after - 1  # last trading day before the holiday
        entry_bar = d_minus_1 - (lookback_days - 1)  # bar we enter AT the close of (D-5 by default)
        hold_start = d_minus_1 - (hold_days - 1)  # D-4 by default
        if entry_bar < 0 or hold_start < 0:
            continue
        # Exposed from the bar AFTER entry_bar (entered at its close)
        # through d_minus_1 inclusive, restricted to the disclosed
        # [D-(hold_days-1) .. D-1] holding window.
        start_i = max(entry_bar + 1, hold_start)
        end_i = d_minus_1
        if start_i > end_i:
            continue
        position.iloc[start_i : end_i + 1] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs).

    Unlike most strategies in this repo, the position series here is
    already forward-looking-safe by construction (each holding window is
    defined purely from the trading calendar, not from any today's-close
    signal), so no additional shift is applied beyond the standard
    open/close return convention: the position held on day t earns day t's
    close-to-close return.
    """
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position * daily_ret
    return strategy_ret
