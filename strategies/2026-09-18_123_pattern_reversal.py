"""Strategy: 123 Pattern Bullish Reversal (three-swing structural reversal).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-090):
Per quantifiedstrategies.com's "123 Pattern Reversal Trading Strategy"
(https://www.quantifiedstrategies.com/123-pattern-reversal-strategy/):
a bullish 123 reversal is confirmed by a specific 4-bar low/high structural
break -- source's own disclosed mechanical rule (backtested there on GLD):
  - Today's low < yesterday's low
  - Yesterday's low < the low from 3 days ago
  - The low from 2 days ago < the low from 3 days ago
  - The high from 2 days ago < the high from 3 days ago
This captures the "swing point 3 breaks structure but yesterday makes a
fresh new low relative to 3-days-ago, while 2-days-ago carved out a lower
high" fingerprint of an emerging bullish reversal (double-bottom-like).
Source used a simple N-day time exit (no target/stop) and reported the
20-day exit as the best profit factor (2.22) on GLD. We adapt this exactly
as disclosed, generalized to any OHLC price_df, long-only, with the N-day
exit as a tunable parameter. First 123-pattern / structural-swing-break
strategy in this repo -- distinct from all NR-family (range-contraction),
outside-day, and pure double-bottom/support-bounce entries already tested,
since this is a specific 4-bar low/high sequence condition rather than a
volatility-range or level-touch condition.

Signal logic
------------
- entry_condition (evaluated each bar t, using lows/highs at t, t-1, t-2, t-3):
    low[t]   < low[t-1]
    low[t-1] < low[t-3]
    low[t-2] < low[t-3]
    high[t-2] < high[t-3]
  All four must hold simultaneously -> enter long at next bar's open (we use
  next-bar-close-equivalent via shift(1) return convention, consistent with
  every other strategy in this repo).
- Exit: fixed N-day time exit (max_hold_days), exactly as the source's own
  backtest methodology (no separate stop/target disclosed beyond the N-day
  sweep).
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
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    low = df["low"]
    high = df["high"]

    low_t = low
    low_t1 = low.shift(1)
    low_t2 = low.shift(2)
    low_t3 = low.shift(3)
    high_t2 = high.shift(2)
    high_t3 = high.shift(3)

    entry_condition = (
        (low_t < low_t1)
        & (low_t1 < low_t3)
        & (low_t2 < low_t3)
        & (high_t2 < high_t3)
    ).fillna(False)

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
