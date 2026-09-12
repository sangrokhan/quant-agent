"""Strategy: N-day-high breakout with a FIXED holding horizon (not a trailing
exit), on BTC/ETH and equity indices, per Quantpedia's "Revisiting
Trend-following and Mean-reversion Strategies in Bitcoin" (12 Sep 2024),
https://quantpedia.com/revisiting-trend-following-and-mean-reversion-strategies-in-bitcoin/?a=6080

Hypothesis (knowledge_base id 2026-09-12-207):
Quantpedia's "MAX strategy" methodology: on any day t where the close
reaches a new x-day maximum (x in {10,20,30,40,50}), the forward return over
the *same* x-day horizon tends to be positive on average (trend-following
continuation), and this "buy-the-new-high, hold-for-x-days" effect was found
to remain "alive and effective" for BTC out to Aug 2024, especially at the
10-day lookback, even out-of-sample through the 2022-2024 stress period.

This is DISTINCT from prior accepted/rejected Donchian entries in this log
(2026-09-04-054 plain 20/10 asymmetric Donchian; 2026-09-06-125 Turtle
System-1 with ATR stop) because:
  - Entry and exit windows are the SAME length x (symmetric), not
    asymmetric 20-in/10-out.
  - Exit is a FIXED time-based horizon (hold exactly x bars then flatten),
    not a rolling low-breakout or ATR trailing stop.
  - Re-entry only fires once flat AND a fresh new x-day high prints.

Signal logic
------------
- rolling_max = close.rolling(x, min_periods=x).max()
- new_high = close >= rolling_max (today's close IS the x-day max)
- Enter long (if flat) when new_high fires.
- Once in, hold exactly `hold_days` bars (default: hold_days == lookback,
  matching the Quantpedia same-horizon methodology), then force-flat for at
  least one bar before a new entry can fire again (avoids instant re-entry
  every single day during a strong uptrend, which would degenerate into
  "always long").

Interface contract (validation/grid_test.py + validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
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


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 10,
    hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rolling_max = close.rolling(lookback, min_periods=lookback).max()
    new_high = (close >= rolling_max) & rolling_max.notna()

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = -1
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(new_high.iloc[i]):
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
