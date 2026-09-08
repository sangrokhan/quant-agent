"""Strategy: Turnaround Tuesday/Wednesday (3-day-down-streak reversal).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-135):
Per https://www.quantitativo.com/p/turnaround-tuesdays-on-steroids
(Quantitativo's own verified re-test of the "Turnaround Tuesday" blog
strategy, then their own improvement): the author's modified entry rule
(found via trying "all possible combinations" of days-of-week and
consecutive-down-day counts) that worked best:
  1. Today is Tuesday OR Wednesday.
  2. Yesterday's close < close 2 days ago.
  3. Close 2 days ago < close 3 days ago.
  (i.e. a 3-consecutive-day decline sequence, checked as of yesterday.)
  4. Go long at the open (approximated here as at yesterday's close, since
     this repo's daily-bar strategies trade close-to-close, consistent
     with every other strategy file in strategies/).
  5. Exit when close > yesterday's high (the source's own stated exit
     rule, a fast single-bar-recovery exit -- NOT a fixed hold_days).

This is DISTINCT from the already-accepted plain Down-Monday->Tuesday
reversal (2026-09-08-116, single-day-down trigger, hold_days=1 fixed exit)
via: (a) a 3-consecutive-day-decline requirement instead of a single down
day, (b) trading on BOTH Tuesday and Wednesday rather than only Tuesday
(the source's own finding after testing all day-of-week combinations), and
(c) a signal-based "close > yesterday's high" exit instead of a fixed
1-day hold. Per the source's own QQQ backtest: Sharpe 1.52, 11.4% annual
return (vs 9.2% buy-and-hold), 70%+ win rate, 15 trades/year.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
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
    trade_tuesday: bool = True,
    trade_wednesday: bool = True,
    down_streak_days: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    weekday = pd.Series(df.index.dayofweek, index=close.index)  # Mon=0 ... Sun=6
    allowed_day = pd.Series(False, index=close.index)
    if trade_tuesday:
        allowed_day |= weekday == 1
    if trade_wednesday:
        allowed_day |= weekday == 2

    # down_streak_days consecutive strictly-declining closes ending yesterday
    # (close[t-1] < close[t-2] < ... < close[t-down_streak_days]).
    down_streak = pd.Series(True, index=close.index)
    for k in range(1, down_streak_days):
        down_streak &= close.shift(k) < close.shift(k + 1)

    entry = allowed_day & down_streak.fillna(False)
    exit_signal = close > high.shift(1)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
