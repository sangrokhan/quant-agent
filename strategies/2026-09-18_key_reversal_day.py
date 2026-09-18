"""Strategy: Bullish Key Reversal Day (single-bar exhaustion reversal).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-092):
Per quantifiedstrategies.com's "Key Reversal Day Pattern" article
(https://www.quantifiedstrategies.com/reversal-day-trading-strategy/):
a Bullish Key Reversal Day (selling climax) is a single-bar exhaustion
pattern where price makes a new low relative to the prior day (testing
support / a fresh lower low) but then closes ABOVE the previous day's
high (full reversal within one session, signaling the prior downtrend has
exhausted itself and buyers took control). Source's own disclosed
mechanical rule and backtest (on GLD): entry on a bullish key reversal
day, N-day time exit; source reports an optimal exit window of 24 trading
days with average trade +2.02% and profit factor > 1.0 for the bullish
setup specifically (the bearish/mirror setup underperformed due to
"overnight upward drift" and is explicitly NOT adapted here -- long-only
bullish setup only, consistent with this repo's stock-market long bias).
First single-bar Key Reversal Day strategy in this repo -- distinct from
the 123 Pattern (2026-09-18-090/091, a 4-bar structural low/high sequence)
and from all NR/outside-day entries (range-contraction/expansion
conditions, not a low-then-reversal-close condition).

Signal logic
------------
- Entry (long): today's low < yesterday's low (fresh lower low) AND
  today's close > yesterday's high (full intraday reversal, closing above
  yesterday's entire range).
- Exit: fixed N-day time exit (max_hold_days), per source's own
  N-day-exit backtest methodology (no separate stop/target disclosed).
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
    max_hold_days: int = 24,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    low = df["low"]
    high = df["high"]
    close = df["close"]

    low_prev = low.shift(1)
    high_prev = high.shift(1)

    entry_condition = ((low < low_prev) & (close > high_prev)).fillna(False)

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
