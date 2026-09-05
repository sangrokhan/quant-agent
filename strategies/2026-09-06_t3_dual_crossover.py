"""Strategy: T3 (Tillson) dual moving-average crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-108),
sourced from search snippets of:
  - WH SelfInvest's T3 Moving Average and Histogram article: "This example
    shows the crossing version of the Tillson moving average. When the
    fast T3 crosses the slow T3 upwards, the trend is positive. This is a
    buy signal."
  - TradingView "Tillson T3 Moving Average MTF" description: "When the fast
    T3 crosses the slower one from below and edges higher, this is called a
    Golden Cross and produces a bullish entry signal."

Distinct from this repo's already-tested T3/Coral variants: 2026-09-04-131
("Coral" slope-flip color-coded trigger, single T3 line) and 2026-09-05-090
(single T3 line, price-crosses-T3 trigger). This is a genuine DUAL-LINE (fast
T3 period vs slow T3 period) crossover, mechanically analogous to a
fast/slow EMA crossover but using Tillson's T3 smoothing (a sextuple
cascaded EMA recombined via a fixed polynomial of a volume-factor constant
b, default 0.7) for reduced lag relative to a plain EMA of the same period.

Signal logic
------------
- T3(close, period, b) = sextuple-cascaded-EMA polynomial recombination
  (Tillson's original formula; see `_t3` below).
- fast_t3 = T3(close, fast_period, b); slow_t3 = T3(close, slow_period, b).
- Long entry: fast_t3 crosses above slow_t3 (Golden Cross).
- Exit: fast_t3 crosses back below slow_t3 (Death Cross), or a
  max_hold_days time-stop (repo standard safety valve; sources give no
  explicit stop-loss/time-stop rule of their own).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _t3(close: pd.Series, period: int, volume_factor: float) -> pd.Series:
    e1 = close.ewm(span=period, adjust=False, min_periods=period).mean()
    e2 = e1.ewm(span=period, adjust=False, min_periods=period).mean()
    e3 = e2.ewm(span=period, adjust=False, min_periods=period).mean()
    e4 = e3.ewm(span=period, adjust=False, min_periods=period).mean()
    e5 = e4.ewm(span=period, adjust=False, min_periods=period).mean()
    e6 = e5.ewm(span=period, adjust=False, min_periods=period).mean()

    b = volume_factor
    c1 = -(b ** 3)
    c2 = 3 * b ** 2 + 3 * b ** 3
    c3 = -6 * b ** 2 - 3 * b - 3 * b ** 3
    c4 = 1 + 3 * b + b ** 3 + 3 * b ** 2

    t3 = c1 * e6 + c2 * e5 + c3 * e4 + c4 * e3
    return t3


def generate_signals(
    price_df: pd.DataFrame,
    fast_period: int = 10,
    slow_period: int = 30,
    volume_factor: float = 0.7,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fast_t3 = _t3(close, fast_period, volume_factor)
    slow_t3 = _t3(close, slow_period, volume_factor)

    crossed_up = (fast_t3 > slow_t3) & (fast_t3.shift(1) <= slow_t3.shift(1))
    crossed_down = (fast_t3 < slow_t3) & (fast_t3.shift(1) >= slow_t3.shift(1))

    entry_arr = crossed_up.fillna(False).values
    exit_arr = crossed_down.fillna(False).values

    n = len(df)
    position = np.zeros(n, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if not in_pos:
            if entry_arr[i]:
                in_pos = True
                hold_count = 0
        else:
            hold_count += 1
            if exit_arr[i] or hold_count >= max_hold_days:
                in_pos = False
        position[i] = 1 if in_pos else 0

    return pd.Series(position, index=df.index, name="position")


def generate_returns(
    price_df: pd.DataFrame,
    fast_period: int = 10,
    slow_period: int = 30,
    volume_factor: float = 0.7,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        fast_period=fast_period,
        slow_period=slow_period,
        volume_factor=volume_factor,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns.name = "strategy_returns"
    return strat_returns
