"""Strategy: "Down Monday -> Tuesday Reversal" day-of-week seasonality.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-116):
Per https://www.quantifiedstrategies.com/tuesday-reversals-in-sp-500/ (SPY
backtest 2000-2024ish) and the broader weekday-effect survey at
https://www.quantifiedstrategies.com/day-of-the-week-effect/, the S&P 500
(and by extension other index-tracking ETFs) shows a strong "Turnaround
Tuesday" mean-reversion pattern: when Monday's close is LOWER than the prior
Friday's close (a "down Monday"), buying at Monday's close and holding to
Tuesday's close produces a positive average return (source's own SPY table:
average +0.11% with the Monday-down-day filter, vs a smaller unconditional
Tuesday average of +0.11-0.17% without the filter -- the filter is reported
to sharpen the win rate to ~55-60%). This is a pure calendar-effect
strategy: no price/volume indicator, purely day-of-week + prior-day-return
conditioning. This is the first pure day-of-week seasonality strategy in
this repo (weekday-effect angle previously untested; "turn of month" and
"gap" seasonality strategies exist but not weekday-specific mean reversion).

Signal logic
------------
- Weekday is derived from the DataFrame's DatetimeIndex.
- "Down Monday": weekday == Monday AND that Monday's close < the close of
  the most recent prior trading session (captures the "Friday's close"
  comparison even around holiday-shortened weeks, where the prior session
  might not literally be a Friday).
- Entry (long): at the close of a "down Monday".
- Exit: at the close of the very next trading session (intended to be
  Tuesday; this also degrades gracefully in holiday weeks where the next
  session isn't literally a Tuesday).
- Flat otherwise. Only ever in the market 1 trading day per triggered week
  (long-only, no shorting -- see SAFETY.md, this is a backtest-only
  strategy, no order placement).
- ``hold_days`` param (default 1) lets the grid test whether extending the
  hold past a single day changes the edge (the source only tested a
  1-day hold, so hold_days=1 is the primary/literal replication).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    return df


def generate_signals(
    price_df: pd.DataFrame,
    hold_days: int = 1,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry triggered at the close of a "down Monday" (Monday's close
    below the prior session's close); held for ``hold_days`` trading
    sessions, then flat until the next trigger.
    """
    df = _prep(price_df)
    close = df["close"]
    weekday = pd.Series(df.index.weekday, index=df.index)  # Monday=0

    prev_close = close.shift(1)
    is_monday = weekday == 0
    down_monday = is_monday & (close < prev_close)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(down_monday.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias -- can't trade on today's own close).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
