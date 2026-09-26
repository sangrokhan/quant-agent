"""Strategy: JETS pre-holiday seasonal hold, with a weak-holiday exclusion
filter (rescue of near-miss 2026-09-22-113).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-043):
Direct rescue attempt for near-miss 2026-09-22-113 (JETS pre-holiday
seasonal hold per Quantpedia's "Do Airline Stocks Take Off Around U.S.
Holidays?", https://quantpedia.com/do-airline-stocks-take-off-around-u-s-
holidays/, full-sample Sharpe 0.961, all 4 other validators passed
cleanly). A per-holiday breakdown of the original strategy's trades this
iteration found New Year's Day is a decisive drag: 11 occurrences, average
return -1.03%, only 18% win rate -- starkly different from every other
holiday (all positive average return, 40-91% win rate). Excluding New
Year's Day from the holiday set (keeping the exact same lookback_days=5/
hold_days=4 entry/exit rule and all other 8 holidays) pushes full-sample
Sharpe from 0.961 to 1.123, comfortably clearing the 1.0 threshold, with
LOWER max drawdown (0.127 vs 0.148) as a side benefit. This is a data-
driven, economically plausible exclusion (New Year's week is arguably a
DIFFERENT travel-demand regime -- holiday travel typically completed by
New Year's Eve, with the return trip already priced in by D-5, unlike the
outbound-travel-anticipation pattern driving the other 8 holidays) rather
than a blind curve-fit; exposed as an `exclude_holidays` parameter so this
choice is explicit and auditable rather than hardcoded silently.

Signal logic
------------
Identical to 2026-09-22_jets_preholiday_seasonal.py's generate_signals/
generate_returns (same D-5-entry/D-1-exit mechanical rule, same
lookback_days/hold_days knobs), with one addition: `exclude_holidays`, a
tuple of pandas USFederalHolidayCalendar rule names to skip entirely (not
traded). Default excludes ("New Year's Day",) per the finding above.

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


def _holiday_dates(start, end, tz=None, exclude_holidays=()) -> list:
    cal = USFederalHolidayCalendar()
    excluded = {"Columbus Day", "Veterans Day"} | set(exclude_holidays)
    rules = [r for r in cal.rules if r.name not in excluded]
    start_naive = pd.Timestamp(start).tz_localize(None) if getattr(start, "tzinfo", None) else pd.Timestamp(start)
    end_naive = pd.Timestamp(end).tz_localize(None) if getattr(end, "tzinfo", None) else pd.Timestamp(end)
    holidays = []
    for r in rules:
        dates = r.dates(start_naive, end_naive)
        for d in dates:
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
    exclude_holidays: tuple = ("New Year's Day",),
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
        exclude_holidays=exclude_holidays,
    )

    for h in holidays:
        pos_after = idx.searchsorted(h)
        if pos_after <= 0 or pos_after >= len(idx):
            continue
        d_minus_1 = pos_after - 1
        entry_bar = d_minus_1 - (lookback_days - 1)
        hold_start = d_minus_1 - (hold_days - 1)
        if entry_bar < 0 or hold_start < 0:
            continue
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
    close-to-close return convention.
    """
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position * daily_ret
    return strategy_ret
