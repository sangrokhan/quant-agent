"""Strategy: Easter Holiday Week seasonal effect (long into Holy Thursday close).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-XXX):
Per QuantifiedStrategies.com's "Easter Trading Strategy: Does the Stock
Market Rally Before the Holiday?"
(https://quantifiedstrategies.substack.com/p/easter-trading-strategy-does-the,
read via browser_exec this iteration -- web_search DDGS/Yahoo backend
TLS-errored on every query attempted): because Good Friday is a US market
holiday, the trading week concludes on Holy Thursday, which historically
stands out as one of the strongest trading days of the year (increased
investor optimism, lower volume, institutional holiday-period behavior).
Source's own disclosed rule ("Backtest 2: The Easter Holiday Week
Performance"): buy stocks at the close of the Friday PRECEDING Easter week
(i.e. the Friday about 6 calendar days before Good Friday), sell at the
close of Holy Thursday (the trading day immediately before Good Friday).
Source's own S&P 500 backtest since 1960: avg gain/trade 0.7% (65yr),
rising to 1.3% (since 2000), max drawdown as low as 2%. This is a novel
calendar-anomaly construction for this repo (no prior Easter/Good-Friday
entry) -- Easter's date is computed via the standard Gauss/Anonymous
Gregorian algorithm (no external calendar data dependency) each year in the
backtest window, and the actual entry/exit are the nearest available
trading days on/before the target calendar dates.

Signal logic
------------
- For each year in the price data's date range, compute Easter Sunday
  (Gregorian Computus algorithm), then Good Friday = Easter - 2 days,
  Holy Thursday = Easter - 3 days, and the entry Friday = Good Friday - 7
  calendar days (the Friday of the week BEFORE Holy Week).
- Entry (long): on the first trading day at or after the entry Friday
  (holding through any earlier market closures), enter at that day's
  close.
- Exit: at the close of the last trading day at or before Holy Thursday
  (i.e. the day immediately preceding Good Friday's market closure).
- Flat all other days. No parameters materially change this beyond a
  window-widening/narrowing knob (days_before_good_friday) for
  parameter-sensitivity testing.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _easter_sunday(year: int) -> date:
    """Anonymous Gregorian algorithm (Computus) for the date of Easter Sunday."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def generate_signals(
    price_df: pd.DataFrame,
    days_before_good_friday: int = 7,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    idx = pd.to_datetime(close.index).tz_localize(None)
    close_reidx = close.copy()
    close_reidx.index = idx

    years = range(idx.min().year, idx.max().year + 1)
    position = pd.Series(0, index=close_reidx.index, dtype=int)

    for year in years:
        easter = _easter_sunday(year)
        good_friday = easter - timedelta(days=2)
        holy_thursday = easter - timedelta(days=3)
        entry_friday = good_friday - timedelta(days=days_before_good_friday)

        entry_ts = pd.Timestamp(entry_friday)
        exit_ts = pd.Timestamp(holy_thursday)

        entry_candidates = close_reidx.index[close_reidx.index >= entry_ts]
        exit_candidates = close_reidx.index[close_reidx.index <= exit_ts]
        if entry_candidates.empty or exit_candidates.empty:
            continue
        entry_day = entry_candidates[0]
        exit_day = exit_candidates[-1]
        if entry_day > exit_day:
            continue
        position.loc[entry_day:exit_day] = 1

    position.index = close.index
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # Entry is intended to happen AT the entry day's own close (per source's
    # own rule: "buy at close of Friday preceding Easter week") -- so the
    # position becomes active starting the NEXT trading day's return, same
    # as every other strategy in this repo (shift-by-1 avoids look-ahead).
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
