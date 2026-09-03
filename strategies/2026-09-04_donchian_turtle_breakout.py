"""Strategy: Donchian Channel breakout (Turtle Trader 20/10 asymmetric rule).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-054):
Per InvestingPaths' Donchian breakout article: the classic 1983 Turtle
Trader system buys at the close when price makes a new N-day high, and
exits on a new M-day low (asymmetric entry/exit lookback windows -- the
original system's trailing exit). Standard params: entry_window=20,
exit_window=10. This is a pure breakout/trend-following system with no
mean-reversion assumption, distinct from every prior band/oscillator
construction already tested in this repo.

Rule:
    entry: close == rolling_max(high, entry_window)  (new N-day high)
    exit:  close == rolling_min(low, exit_window)     (new M-day low)
    Stay long between an entry and the next exit signal.

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
    entry_window: int = 20,
    exit_window: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    entry_high = high.rolling(entry_window).max()
    exit_low = low.rolling(exit_window).min()

    # New N-day high: close at/above the trailing max of the prior window
    # (shifted by 1 to avoid look-ahead: today's own high can't confirm
    # today's own breakout level).
    entry_signal = close >= entry_high.shift(1)
    exit_signal = close <= exit_low.shift(1)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
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
