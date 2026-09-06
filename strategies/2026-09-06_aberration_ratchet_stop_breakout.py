"""Strategy: Aberration (Keith Fitschen, 1986) trend-following breakout with
monotonic trailing-stop exit, long-only.

Hypothesis (see knowledge_base id 2026-09-06-144):
Per Concretum Research's Substack article "How to Size Your Trend Trades"
(https://concretumgroup.substack.com/p/how-to-size-your-trend-trades):
"The Aberration strategy is a trend-following framework developed by Keith
Fitschen in 1986, built on what are effectively Bollinger Bands... Entry
signals are generated when the price moves outside the bands: a breakout
above the upper band triggers a long position... The position is held until
the price crosses the moving average in the direction opposite to the
prevailing trend, which serves as the exit signal... Our sole modification
to the standard rules is to impose a monotonic adjustment of the
moving-average-based stop. For long positions, the stop is permitted to
move only upward... effectively acting as a trailing exit constraint."

Band construction: UB = SMA(sma_window) + std_mult*STD(sma_window);
LB = SMA(sma_window) - std_mult*STD(sma_window). Source default sma_window=50,
std_mult=2.

Signal logic (long-only adaptation; source is long/short)
----------------------------------------------------------
- Entry: close breaks above the upper Bollinger band (UB).
- Exit stop line: the SMA(sma_window), but MONOTONICALLY RATCHETED upward
  while in a long position (running_max of the SMA since entry) -- this is
  the source's own stated modification, distinguishing it from a plain
  "cross back below SMA" exit that would let the stop line fall along with
  a temporarily dipping SMA.
- Exit: close crosses below the ratcheted (non-decreasing) stop line, or a
  max_hold_days time-stop as a safety backstop (source has no explicit
  time-stop, added here per this repo's standard practice).

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 50,
    std_mult: float = 2.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    sma = close.rolling(sma_window).mean()
    std = close.rolling(sma_window).std()
    upper_band = sma + std_mult * std

    breakout = close > upper_band

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    ratchet_stop = np.nan
    for i in range(n):
        if in_position:
            held = i - entry_idx
            cur_sma = sma.iloc[i]
            if not np.isnan(cur_sma):
                ratchet_stop = cur_sma if np.isnan(ratchet_stop) else max(ratchet_stop, cur_sma)
            stop_break = (not np.isnan(ratchet_stop)) and (close.iloc[i] < ratchet_stop)
            if stop_break or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                ratchet_stop = np.nan
                continue
            position.iloc[i] = 1
        else:
            if bool(breakout.iloc[i]):
                in_position = True
                entry_idx = i
                ratchet_stop = sma.iloc[i]
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
