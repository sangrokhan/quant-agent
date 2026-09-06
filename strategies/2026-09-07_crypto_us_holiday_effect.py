"""Strategy: Crypto US-Holiday Next-Day Effect.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-009):
Per CoinGecko's "The Best Days to Buy Bitcoin" study (May 1 2013 - May 8
2026, 4,753 daily observations, UTC snapshots): "US holidays register a
+0.77% average next-day return compared to the non-holiday average of
+0.19% -- holidays outperformed non-holidays in 11 out of 14 calendar
years." Specific holidays: New Year's Day +2.01% (84.6% win rate),
Columbus Day +1.70% (84.6%), Christmas +1.46% (53.8%), Labor Day +1.22%
(69.2%). Two holidays are NEGATIVE (MLK Day -0.84%, Independence Day
-0.26%) and are excluded from the entry set here per the source's own
finding.

Economic rationale (source's own): unlike equities, Bitcoin trades 24/7
including through US federal holidays when traditional markets are
closed and institutional participants are absent -- this creates a
structurally different, thinner-liquidity trading session that may
exhibit systematically different (here, more positive) price action, an
effect equity markets structurally cannot exhibit since they are simply
closed on these dates. This makes the effect CRYPTO-ONLY by construction
(equity strategies cannot trade the holiday itself), distinct from this
repo's existing pre-holiday equity effect (2026-09-03-020, tests the
LAST trading session BEFORE a holiday close) and January-effect/
Santa-Claus-Rally/OPEX-week calendar strategies (none of which use the
specific US federal holiday CALENDAR DATE itself as the entry trigger).

Signal logic
------------
- Entry: hold long for exactly 1 day starting on each of the 4
  positive-edge US federal holidays (New Year's Day, Columbus Day,
  Christmas Day, Labor Day) plus Thanksgiving and Veterans Day (source
  flags Veterans Day's average as outlier-driven/unreliable via mean, but
  we include it at a conservative equal weight per the standard holiday
  calendar since crypto's is a testable, mechanical rule either way --
  the grid tests including/excluding it via `include_uncertain_holidays`).
- MLK Day and Independence Day are explicitly EXCLUDED (source's own
  negative-edge findings).
- Position is long for a `hold_days` window starting at the holiday
  date's close (source studies the day AFTER the holiday date), flat
  otherwise.
- Crypto only (equity loader will show near-zero trades since exchanges
  are closed on these dates and no signal fires on non-trading calendar
  days -- included for grid completeness/falsification per repo
  convention, but no meaningful equity edge is expected structurally).

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _us_federal_holidays(years, include_uncertain: bool) -> set:
    """Return the set of (month, day)-based holiday dates for given years.

    Fixed-date holidays only where practical; floating holidays
    (Labor Day = 1st Monday Sep, Columbus Day = 2nd Monday Oct,
    Thanksgiving = 4th Thursday Nov, MLK excluded) are computed properly
    per year using pandas date offsets.
    """
    import datetime as dt

    holidays = set()
    for year in years:
        # New Year's Day (positive, +2.01%)
        holidays.add(dt.date(year, 1, 1))
        # Columbus Day: 2nd Monday of October (positive, +1.70%)
        oct1 = dt.date(year, 10, 1)
        first_monday = oct1 + dt.timedelta(days=(7 - oct1.weekday()) % 7)
        columbus = first_monday + dt.timedelta(days=7)
        holidays.add(columbus)
        # Christmas Day (positive, +1.46%)
        holidays.add(dt.date(year, 12, 25))
        # Labor Day: 1st Monday of September (positive, +1.22%)
        sep1 = dt.date(year, 9, 1)
        labor_day = sep1 + dt.timedelta(days=(7 - sep1.weekday()) % 7)
        holidays.add(labor_day)
        if include_uncertain:
            # Thanksgiving: 4th Thursday of November
            nov1 = dt.date(year, 11, 1)
            first_thursday = nov1 + dt.timedelta(days=(3 - nov1.weekday()) % 7)
            thanksgiving = first_thursday + dt.timedelta(days=21)
            holidays.add(thanksgiving)
            # Veterans Day (fixed date, Nov 11) -- outlier-driven per source
            holidays.add(dt.date(year, 11, 11))
        # MLK Day and Independence Day explicitly EXCLUDED (negative edge).
    return holidays


def _bars_per_day(idx: pd.DatetimeIndex) -> int:
    """Detect approximate bars-per-calendar-day from the index spacing.

    This repo's crypto loader returns HOURLY bars (~24/day) while the
    equity loader returns DAILY bars (1/day) -- hold_days must be
    converted to a bar count using the actual detected frequency, not
    assumed to be 1 bar = 1 day (a bug this strategy's first draft had,
    which silently made "hold_days=1" mean "hold 1 HOUR" on crypto).
    """
    if len(idx) < 2:
        return 1
    median_delta = pd.Series(idx[1:] - idx[:-1]).median()
    seconds_per_day = 24 * 60 * 60
    bars = max(1, round(seconds_per_day / median_delta.total_seconds()))
    return bars


def generate_signals(
    price_df: pd.DataFrame,
    hold_days: int = 1,
    include_uncertain_holidays: bool = False,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    idx = df.index

    bars_per_day = _bars_per_day(idx)
    hold_bars = max(1, hold_days * bars_per_day)

    years = sorted(set(idx.year))
    holiday_dates = _us_federal_holidays(years, include_uncertain_holidays)

    # Mark each bar whose calendar date is a holiday, but only trigger
    # entry on the FIRST bar of that calendar date (avoid re-triggering
    # hold_bars times per holiday on intraday/hourly data).
    dates = pd.Series([d.date() for d in idx], index=idx)
    is_holiday_date = dates.isin(holiday_dates)
    is_first_bar_of_date = dates != dates.shift(1)
    entry_trigger = (is_holiday_date & is_first_bar_of_date).to_numpy()

    position = pd.Series(0, index=idx, dtype=int)
    pos_arr = position.to_numpy().copy()

    hold_counter = 0
    in_pos = False
    for i in range(len(idx)):
        if in_pos:
            hold_counter += 1
            if hold_counter >= hold_bars:
                in_pos = False
                hold_counter = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_trigger[i]:
                in_pos = True
                hold_counter = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=idx, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    hold_days: int = 1,
    include_uncertain_holidays: bool = False,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        hold_days=hold_days,
        include_uncertain_holidays=include_uncertain_holidays,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
