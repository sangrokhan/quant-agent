"""Strategy: Pre-FOMC Announcement Drift.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-023),
sourced from https://www.quantseeker.com/p/trading-the-fed-the-pre-fomc-drift
(summarizing Lucca & Moench 2015, "The Pre-FOMC Announcement Drift", NY Fed
Staff Report 512): US equities exhibit large, persistent positive excess
returns in the 24 hours before scheduled FOMC meeting announcements --
since 1994, pre-FOMC gains account for over half of total annual realized
excess stock market returns, with no equivalent pattern in bonds/FX/
commodities. The drift does not reverse post-announcement, suggesting
gradual investor positioning ahead of the decision rather than reaction to
new information. Distinct from every other calendar-effect strategy in
this repo (turn-of-month, day-of-week, payday-anomaly, pre-holiday,
Santa-Claus, Halloween) -- this is anchored to a specific recurring
scheduled EVENT (8 FOMC meetings/year), not a fixed calendar date/rank.

Signal logic
------------
- Long entry: close of the trading day `days_before` before a scheduled
  FOMC announcement date (from a hardcoded list of historical FOMC
  meeting end-dates, 2019-2026, sourced from federalreserve.gov meeting
  calendars).
- Exit: close of the FOMC announcement date itself (or `hold_days` after
  entry, whichever the parameterization implies -- kept as a simple fixed
  hold-length window here for grid-testability).
- Flat all other days. Long-only, no shorting.
- Tested on equity (QQQ, SPY -- where the mechanism, Fed-driven US equity
  risk premium, plausibly applies) and crypto (BTC/USDT, ETH/USDT) as a
  falsification check -- crypto isn't a constituent of the US equity risk
  premium Lucca & Moench studied, though a spillover effect is plausible
  given how correlated crypto has become with risk sentiment, so this is a
  genuine open question rather than an obvious-null falsification check.

Interface contract for validators (see validation/validators.py) and grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import pandas as pd

# Historical FOMC meeting announcement (final day of meeting) dates,
# 2019-01-01 through 2026-09-01. Source: federalreserve.gov/monetarypolicy/
# fomccalendars.htm and fomchistorical2019.htm / fomchistorical2020.htm
# (includes 2020's unscheduled emergency meetings on 2020-03-03 and
# 2020-03-15 alongside the regular schedule).
FOMC_DATES = [
    "2019-01-30", "2019-03-20", "2019-05-01", "2019-06-19",
    "2019-07-31", "2019-09-18", "2019-10-30", "2019-12-11",
    "2020-01-29", "2020-03-03", "2020-03-15", "2020-04-29",
    "2020-06-10", "2020-07-29", "2020-09-16", "2020-11-05", "2020-12-16",
    "2021-01-27", "2021-03-17", "2021-04-28", "2021-06-16",
    "2021-07-28", "2021-09-22", "2021-11-03", "2021-12-15",
    "2022-01-26", "2022-03-16", "2022-05-04", "2022-06-15",
    "2022-07-27", "2022-09-21", "2022-11-02", "2022-12-14",
    "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14",
    "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12",
    "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18",
    "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29",
]
FOMC_TIMESTAMPS = pd.to_datetime(FOMC_DATES)


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    days_before: int = 1,
    hold_days: int = 2,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long for `hold_days` trading days starting `days_before` trading days
    prior to each scheduled FOMC announcement date (i.e. entering the
    close of trading-day (announcement_idx - days_before) and holding
    through trading-day (announcement_idx - days_before + hold_days - 1)).
    """
    df = _prep(price_df)
    idx = df.index

    position = pd.Series(0, index=idx, dtype=int)
    idx_normalized = idx.normalize() if hasattr(idx, "normalize") else idx

    fomc_timestamps = FOMC_TIMESTAMPS
    idx_tz = getattr(idx_normalized, "tz", None)
    if idx_tz is not None:
        fomc_timestamps = fomc_timestamps.tz_localize(idx_tz)
    elif getattr(fomc_timestamps, "tz", None) is not None:
        fomc_timestamps = fomc_timestamps.tz_localize(None)

    for fomc_ts in fomc_timestamps:
        # Find the trading-day position at/before the FOMC date (in case
        # the exact FOMC date isn't itself a trading day in this symbol's
        # calendar -- searchsorted with side='right' then step back).
        pos = idx_normalized.searchsorted(fomc_ts, side="right") - 1
        if pos < 0 or pos >= len(idx):
            continue
        entry_pos = pos - days_before
        if entry_pos < 0:
            continue
        exit_pos = min(entry_pos + hold_days, len(idx))
        position.iloc[entry_pos:exit_pos] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # Shift position by 1 day: yesterday's signal determines today's exposure
    # (avoid look-ahead bias -- can't trade on today's own close).
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
