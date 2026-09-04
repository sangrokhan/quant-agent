"""Strategy: Buy-Monday-Sell-Friday weekly weekday-effect hold, gated by a
60-day trend filter and a two-sided (goldilocks) volatility-range filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-106):
Per The Rogue Quant's substack backtest of the classic weekday effect
("buy on Monday, sell on Friday" -- markets often dip Monday on weekend
news/position adjustments and recover through the week, with Friday
showing institutional strength pre-weekend), a raw unconditional version
is profitable in gross terms but has a poor Sharpe ratio and long flat
periods. Adding (1) a 60-day trend filter (only buy Mondays when price is
above its own 60-day moving average) and (2) a two-sided volatility-range
filter (skip the trade if the entry day's daily range as a % of price is
below 0.5% or above 3.0% -- a "goldilocks" band, avoiding both dead-quiet
and violently extreme days) reportedly cut drawdowns 30% and improved
profit factor from 1.34 to 1.84 in the source's own NASDAQ futures
backtest.

This is a genuinely distinct construction from every prior day-of-week
strategy already tested in this repo: it holds a FULL Monday-to-Friday
week (5-trading-day horizon) rather than a single overnight/one-day window
(Turnaround Tuesday variants -018/-105 hold only Monday close -> Tuesday
close), and combines BOTH a trend filter and a two-sided volatility-range
filter rather than either alone.

Signal logic
------------
- Trigger day = the first trading day of each week matching `entry_weekday`
  (default 0 = Monday).
- Trend filter: close on the trigger day must be > SMA(trend_window,
  default 60).
- Volatility filter: the trigger day's own daily range as a fraction of
  its close ((high - low) / close) must be within
  [min_range_pct, max_range_pct] (defaults 0.005, 0.03).
- Entry (long): trigger day's close, if BOTH filters pass.
- Exit: close of the exit_weekday (default 4 = Friday) of the SAME week
  (or, if that week has no trading day matching exit_weekday -- e.g. a
  holiday -- the last trading day before the next occurrence of
  entry_weekday).
- Long-only, flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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
    entry_weekday: int = 0,
    exit_weekday: int = 4,
    trend_window: int = 60,
    min_range_pct: float = 0.005,
    max_range_pct: float = 0.03,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    sma = close.rolling(trend_window).mean()
    trend_ok = close > sma

    daily_range_pct = (high - low) / close
    vol_ok = (daily_range_pct >= min_range_pct) & (daily_range_pct <= max_range_pct)

    weekdays = df.index.weekday
    entry_trigger = (weekdays == entry_weekday) & trend_ok.fillna(False) & vol_ok.fillna(False)

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    for i in range(n):
        if in_pos:
            position.iloc[i] = 1
            # Exit at the close of the exit_weekday, OR the last trading day
            # before the next entry_weekday if that week has no exit_weekday
            # trading day (holiday), to avoid holding indefinitely.
            is_exit_day = weekdays[i] == exit_weekday
            is_last_before_next_entry = (
                i + 1 < n and weekdays[i + 1] == entry_weekday and weekdays[i] != entry_weekday
            )
            if is_exit_day or is_last_before_next_entry:
                in_pos = False
        elif bool(entry_trigger.iloc[i]):
            in_pos = True
            position.iloc[i] = 1
        else:
            position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    entry_weekday: int = 0,
    exit_weekday: int = 4,
    trend_window: int = 60,
    min_range_pct: float = 0.005,
    max_range_pct: float = 0.03,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df, entry_weekday=entry_weekday, exit_weekday=exit_weekday,
        trend_window=trend_window, min_range_pct=min_range_pct, max_range_pct=max_range_pct,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
