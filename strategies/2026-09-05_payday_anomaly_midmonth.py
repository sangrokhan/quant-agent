"""Strategy: Payday Anomaly / mid-month (16th) calendar effect.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-022),
sourced from https://quantpedia.com/strategies/payday-anomaly/ (based on the
academic "Payday Anomaly" paper): many US firms pay semi-monthly paychecks
on the 15th of the month, with the retirement-contribution (401k) portion
of that paycheck reaching the market on the following trading day -- the
16th. Quantpedia reports the 16th calendar day is the 3rd-best day of the
month for S&P 500 returns historically. This is a DIFFERENT calendar
mechanism from turn-of-the-month (2026-09-03-006, tested last trading day
of month + first 3 of next) and day-of-week (2026-09-03-018) -- here the
signal fires on a fixed CALENDAR DAY NUMBER in the middle of the month
(around the 15th paycheck date), not a trading-day rank relative to month
boundaries.

Signal logic
------------
- Long-only, calendar-based (not price-based): hold the position during a
  window of `window_days` calendar days centered starting at
  `signal_day` (default 16, the anomaly day itself), flat otherwise.
- Practically: for each bar, compute the calendar day-of-month; go long
  if day-of-month is in [signal_day, signal_day + window_days - 1]
  (inclusive), using the first trading day at/after that calendar date if
  the exact date isn't a trading day (weekends/holidays).
- Tested on equity (mechanism should apply -- payroll/401k contributions)
  and crypto (falsification check -- no payroll cycle drives BTC/ETH demand,
  expect no edge).

Interface contract for validators (see validation/validators.py) and grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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
    signal_day: int = 16,
    window_days: int = 2,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long whenever the bar's calendar day-of-month falls within
    [signal_day, signal_day + window_days - 1] (inclusive); flat otherwise.
    Since trading data only has trading days, this naturally lands on the
    first trading day at/after `signal_day` if that exact calendar date
    isn't a trading day (weekend/holiday).
    """
    df = _prep(price_df)
    idx = df.index
    day_of_month = pd.Series(idx.day, index=idx)

    lo = signal_day
    hi = signal_day + window_days - 1
    in_window = (day_of_month >= lo) & (day_of_month <= hi)

    position = in_window.astype(int)
    position.index = idx
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
