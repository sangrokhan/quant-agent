"""Strategy: Fibonacci Pivot Point breakout, daily bars.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-XXX):
Fibonacci pivot levels (a variant of classic floor-trader pivots using
Fibonacci ratios 0.382/0.618/1.0 of the prior period's range instead of the
standard multipliers) are widely watched intraday support/resistance levels.
Per https://quantengines.com/blog/pivot-point-trading-strategy (read via
browser_exec, web_extract failed -- ddgs backend is search-only): a
breakout through R1 with conviction (close beyond the level) tends to
continue toward R2/R3, with the broken level acting as new support; the
article's own filter is "markets that open above PP tend to trend higher".
Adapted here to a DAILY-bar swing setting (repo has no intraday data): pivot
levels are computed from the PRIOR trading day's (high, low, close); we go
long when today's close breaks above R1 (a strong daily close through the
Fibonacci resistance level, itself only 0.382x the prior day's range above
the pivot -- a much tighter/more reactive level than standard floor pivots),
and exit when close falls back below the central pivot point (the broken
level "should act as support" -- losing it invalidates the breakout) or
after a max holding period. This is the first Fibonacci-pivot-point
strategy in this repo (zero prior index hits; distinct from the 8 prior
Camarilla-pivot entries, which use a different multiplier scheme and
target mean-reversion off H3/L3 rather than breakout off R1).

Signal logic
------------
- PP  = (H_prev + L_prev + C_prev) / 3
- R1  = PP + fib_r1 * (H_prev - L_prev)     (default fib_r1 = 0.382)
- Entry (long): today's close > R1 (computed from yesterday's H/L/C).
- Exit: today's close < PP, OR after max_hold_days trading days.
- Flat otherwise.

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
    fib_r1: float = 0.382,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    # Pivot levels computed from the PRIOR day's H/L/C (avoid lookahead).
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)

    pp = (prev_high + prev_low + prev_close) / 3.0
    r1 = pp + fib_r1 * (prev_high - prev_low)

    entry = close > r1
    exit_signal = close < pp

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_days = 0

    entry_arr = entry.to_numpy()
    exit_arr = exit_signal.to_numpy()
    pos_arr = position.to_numpy().copy()

    for i in range(len(close)):
        if in_position:
            hold_days += 1
            if exit_arr[i] or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_arr[i]:
                in_position = True
                hold_days = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    position = pd.Series(pos_arr, index=close.index, dtype=int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    fib_r1: float = 0.382,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(price_df, fib_r1=fib_r1, max_hold_days=max_hold_days)
    # Trade on next bar's return following today's signal (avoid lookahead:
    # position decided using today's close vs yesterday's pivot, realized on
    # tomorrow's return).
    daily_ret = close.pct_change()
    strat_ret = position.shift(1).fillna(0) * daily_ret
    strat_ret = strat_ret.fillna(0.0)
    return strat_ret
