"""Strategy: Weekly & Daily MACD relative-line crossover (Vitali Apirine, TASC Dec 2017).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-146):
Vitali Apirine's TASC Dec 2017 article "Weekly & Daily MACD" simulates a
weekly-timeframe MACD on a daily-only chart by scaling the MACD lengths up
~5x (WeeklyFastLength=60, WeeklySlowLength=130, vs the classic daily
MACD(12,26)), avoiding the need for actual weekly-resampled data. Source's
own disclosed TradeStation indicator computes:
    DailyMACD  = MACD(close, 12, 26)
    WeeklyMACD = MACD(close, 60, 130)
    RelativeDailyLine = WeeklyMACD + DailyMACD
and alerts when RelativeDailyLine crosses the WeeklyMACD line. The source's
own rationale: this crossover flags when short-term (daily) momentum is
adding to or subtracting from the longer-term (weekly-proxy) momentum
baseline -- i.e., a daily momentum impulse strong enough to move the
combined line through the slower weekly trend line.

This repo has tested several MACD/weekly-trend-filter combinations before
(Elder Triple Screen 2026-09-04-044/2026-09-09-007, Quantpedia weekly-MACD
trend filter 2026-09-12-192) but NONE use this specific additive
"RelativeDailyLine = WeeklyMACD + DailyMACD, crossed against WeeklyMACD
itself" construction -- those prior entries use the weekly/longer MACD only
as a binary trend GATE for a separate daily trigger, never combine the two
MACD lines additively into a single crossover signal the way this source
does. Source itself provides only an indicator/alert (no explicit strategy
entry/exit rule) -- our own addition (flagged as such): long entry on
RelativeDailyLine crossing above WeeklyMACD, exit on the reverse cross or
a max_hold_days time-stop.

Source: https://traders.com/Documentation/FEEDbk_docs/2017/12/TradersTips.html
(TradeStation section, read via browser_exec).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _macd(close: pd.Series, fast: int, slow: int) -> pd.Series:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    return ema_fast - ema_slow


def generate_signals(
    price_df: pd.DataFrame,
    daily_fast: int = 12,
    daily_slow: int = 26,
    weekly_fast: int = 60,
    weekly_slow: int = 130,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    daily_macd = _macd(close, daily_fast, daily_slow)
    weekly_macd = _macd(close, weekly_fast, weekly_slow)
    relative_line = weekly_macd + daily_macd

    cross_over = (relative_line > weekly_macd) & (relative_line.shift(1) <= weekly_macd.shift(1))
    cross_under = (relative_line < weekly_macd) & (relative_line.shift(1) >= weekly_macd.shift(1))

    entry = cross_over.fillna(False)
    exit_cross = cross_under.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
