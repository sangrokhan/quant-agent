"""Strategy: Lower Highs & Lower Lows 3-Day Reversal (short-term bounce).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-093):
Per quantifiedstrategies.com's "Lower Highs And Lower Lows Pattern Trading
Strategy" (https://www.quantifiedstrategies.com/lower-highs-and-lower-lows-pattern/):
three consecutive daily bars each making a lower high AND a lower low than
the prior bar (a short-term "stair-step down" exhaustion pattern) tend to
mark a short-term reversal, per the source's own disclosed backtest
methodology on SPY/GLD/TLT: "go long at the close of the third consecutive
lower low and lower high [day], sell after n bars." Source found this
3-consecutive-day version outperformed both the 1-day and 2-day variants
(better average gain, better profit factor, and notably low max drawdown
~9.9% at a 1-day hold on SPY) -- the exact numeric thresholds/tables are
paywalled, but the mechanical entry/exit rule itself (3-in-a-row
lower-high+lower-low, enter at close of day 3, N-day time exit) is fully
disclosed in the free article text. First Lower-Highs/Lower-Lows
structural-reversal strategy in this repo -- distinct from the 123 Pattern
(non-consecutive 4-bar low/high sequence with a specific inequality
structure) and Key Reversal Day (single-bar intraday full reversal).

Signal logic
------------
- A day is a "down day" if high[t] < high[t-1] AND low[t] < low[t-1].
- Entry (long): three consecutive down days (days t-2, t-1, t all down
  days relative to their own prior day) -> enter at close of day t.
- Exit: fixed N-day time exit (max_hold_days), per source's own N-bar-exit
  backtest methodology.
- Flat otherwise; long-only, no re-entry while already in a position.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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
    max_hold_days: int = 10,
    consecutive_days: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    low = df["low"]
    high = df["high"]

    down_day = ((high < high.shift(1)) & (low < low.shift(1))).fillna(False)

    # rolling count of consecutive down days ending at t
    streak = pd.Series(0, index=down_day.index, dtype=int)
    count = 0
    for i in range(len(down_day)):
        if bool(down_day.iloc[i]):
            count += 1
        else:
            count = 0
        streak.iloc[i] = count

    entry_condition = streak >= consecutive_days

    position = pd.Series(0, index=low.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(low)):
        if in_position:
            held = i - entry_idx
            if held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_condition.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs).

    ``leverage_cap`` (default 1.0) scales notional exposure, following this
    repo's established leverage-cap pattern for crypto max-drawdown control.
    """
    leverage_cap = kwargs.pop("leverage_cap", 1.0)
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret * leverage_cap
    return strategy_ret
