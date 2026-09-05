"""Strategy: Qstick Indicator (Tushar Chande) signal-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-105),
sourced from https://www.quantifiedstrategies.com/qstick-indicator-strategy/
("The Qstick indicator is simply the difference between the simple or
exponential moving average of the difference between the open and closing
prices ... QSI = SMA or EMA of (Close - Open) ... We buy when the Qstick
indicator crosses above the signal line. We sell and move to cash when the
signal line crosses under the Qstick indicator." Source backtest used a
100-day MA of (close-open) with a 50-day signal line MA of Qstick itself,
on SPY, EMA variant slightly outperforming SMA: CAGR 6.98%, MDD 35.29%).

First Qstick strategy tested in this repo -- distinct from all prior
dual-moving-average-crossover families (EMA/DEMA/TEMA/ZLEMA/HMA/etc, which
all operate directly on the CLOSE price series) because Qstick's underlying
series is the per-bar (close-open) buying/selling-pressure differential, not
price itself -- a genuinely different signal construction (candlestick body
direction/strength averaged over time), even though the final trigger
(fast line crosses slow line) is mechanically similar to those families.

Signal logic
------------
- Qstick[t] = EMA(close - open, qstick_window)[t]  (source found EMA
  slightly outperforms SMA, so EMA is used as primary; qstick_window is
  tunable, default 100 per source).
- Signal[t] = EMA(Qstick, signal_window)[t]  (signal_window < qstick_window,
  default 50 per source).
- Long entry: Qstick crosses above Signal.
- Exit: Signal crosses back above Qstick (source's own exit rule), or a
  max_hold_days time-stop (repo standard safety valve, source's own backtest
  had no explicit stop and suffered a 35-41% MDD, so this repo adds one).

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


def _qstick(df: pd.DataFrame, qstick_window: int, signal_window: int) -> tuple[pd.Series, pd.Series]:
    body = df["close"] - df["open"]
    qstick = body.ewm(span=qstick_window, adjust=False, min_periods=qstick_window).mean()
    signal = qstick.ewm(span=signal_window, adjust=False, min_periods=signal_window).mean()
    return qstick, signal


def generate_signals(
    price_df: pd.DataFrame,
    qstick_window: int = 100,
    signal_window: int = 50,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    if "open" not in df.columns:
        # Some crypto loaders may not expose an 'open' column identically
        # named -- fail loudly rather than silently producing a flat series.
        raise KeyError("price_df must contain an 'open' column for Qstick")

    qstick, signal = _qstick(df, qstick_window, signal_window)

    crossed_up = (qstick > signal) & (qstick.shift(1) <= signal.shift(1))
    crossed_down = (signal > qstick) & (signal.shift(1) <= qstick.shift(1))

    entry_arr = crossed_up.fillna(False).values
    exit_arr = crossed_down.fillna(False).values

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0

    for i in range(len(df.index)):
        if in_position:
            hold_count += 1
            if exit_arr[i] or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_arr[i]:
                in_position = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **params)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
