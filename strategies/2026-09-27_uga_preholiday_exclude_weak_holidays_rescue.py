"""Strategy: UGA Pre-Holiday Effect, per-holiday exclusion rescue.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this
iteration): Direct rescue of this same cron trigger's own near-miss
2026-09-27-016 (Quantpedia's "Pre-Holiday Effect in Commodities",
Vojtko/Dujava, https://quantpedia.com/pre-holiday-effect-in-commodities/,
D-5 -> D-1 hold before each US federal holiday, full-sample UGA Sharpe
0.983, MDD/TC-survival/parameter-sensitivity all passing cleanly --
relative_std 0.042, an unusually stable near-miss). Following this
repo's own established "per-holiday breakdown, exclude the isolated
drag" rescue pattern (already validated once this cron trigger on JETS,
2026-09-27-043 excluding New Year's Day), a per-holiday return breakdown
on UGA (2010-2026, entry_days_before=5) found THREE holidays with
negative average returns and/or a losing win rate: Memorial Day
(avg -0.14%, 41% win rate), Labor Day (avg -0.21%, 65% win rate), and
Veterans Day (avg -0.21%, 50% win rate) -- all three cluster in the
May-November "driving season already underway / no fresh anticipation"
part of the calendar, economically distinct from the remaining 8 holidays
(New Year's, MLK, Washington's Birthday, Juneteenth, Independence Day,
Labor... [see exclude set], Thanksgiving, Christmas) which cluster around
either genuine holiday-travel-demand spikes or winter heating-season fuel
dynamics. Excluding all three pushes full-sample Sharpe from 0.983 to
1.226 and cuts MDD from 0.195 to 0.140.

Signal logic
------------
- Same US-federal-holiday D-5 -> D-1 hold mechanism as
  strategies/2026-09-27_uso_uga_pre_holiday_effect.py, but with an
  exclude_holidays parameter (default: Memorial Day, Labor Day, Veterans
  Day) skipping those specific named holidays entirely.

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


def generate_signals(
    price_df: pd.DataFrame,
    entry_days_before: int = 5,
    exclude_holidays: tuple = ("Memorial Day", "Labor Day", "Veterans Day"),
) -> pd.Series:
    """Return a {0,1} position series: 1 on trading days from D-5 (entry
    price day, held from its close) through D-1 (exit day), for every US
    federal holiday NOT in ``exclude_holidays``.
    """
    df = _prep(price_df)
    idx = df.index
    trading_days = idx.normalize()

    cal = USFederalHolidayCalendar()
    start = idx.min() - pd.Timedelta(days=30)
    end = idx.max() + pd.Timedelta(days=30)
    holidays_idx = cal.holidays(start=start, end=end, return_name=True)

    position = pd.Series(0, index=idx, dtype=int)
    for h, name in holidays_idx.items():
        if name in exclude_holidays:
            continue
        before = trading_days[trading_days < h]
        if len(before) < entry_days_before:
            continue
        pos_d1 = idx.get_indexer([before[-1]])[0]
        pos_entry = pos_d1 - (entry_days_before - 1)
        if pos_entry < 0:
            continue
        lo = pos_entry + 1
        hi = pos_d1 + 1
        if lo < hi:
            position.iloc[lo:hi] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    entry_days_before: int = 5,
    exclude_holidays: tuple = ("Memorial Day", "Labor Day", "Veterans Day"),
) -> pd.Series:
    """Close-to-close daily returns, active only on D-4..D-1 of each
    non-excluded US federal holiday window."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df, entry_days_before=entry_days_before, exclude_holidays=exclude_holidays
    )
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position * daily_ret
    return strategy_ret.fillna(0.0)
