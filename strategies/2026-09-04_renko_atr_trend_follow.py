"""Strategy: ATR-brick Renko trend-following with 200-SMA filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-086):
Per Google's AI-overview summary of TheStopHunter/Tradinformed Renko
trend-following guides: reconstructing price into fixed-size "bricks"
(ATR-based brick size) strips out time-axis noise and clarifies trend
structure; a long entry triggers when price/bricks are entirely above a
200-period SMA (trend filter) AND two consecutive same-direction (up)
bricks form after an opposite-direction (down) brick -- a fresh-momentum
confirmation. Exit on the first down-brick after being long (a color-flip
exit). First Renko-style strategy tested in this repo -- distinct from
every prior trend-following strategy because the trigger is a
price-magnitude-based brick sequence (reconstructed here from daily
OHLCV, since true tick-based Renko charts aren't available from this
repo's daily-bar data source) rather than a time-indexed indicator cross.

Signal logic
------------
- brick_size = ATR(atr_window) at each point (recomputed daily, using a
  rolling ATR rather than a single fixed brick size, since ATR itself
  changes over the long backtest window)
- Reconstruct a running "renko level" and brick-direction sequence:
  starting from the first close, if close moves up by >= 1 brick_size
  from the last renko level, add an up-brick (direction=+1) and advance
  the level; symmetric for down-bricks. Multiple bricks can form on
  a single volatile day (rare but possible).
- sma200 = SMA(close, trend_window)
- Entry (long): close > sma200 (trend filter) AND at least
  `confirm_bricks` consecutive up-bricks have just formed (a fresh
  brick-direction flip from down to up, sustained for confirm_bricks).
- Exit: the first down-brick forms (color-flip), OR close drops below
  sma200 (trend filter break).
- Long-only, flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def _renko_bricks(close: pd.Series, brick_size: pd.Series) -> pd.Series:
    """Return a per-day brick-direction series: +1 for up-brick day,
    -1 for down-brick day, 0 for no new brick formed."""
    n = len(close)
    directions = pd.Series(0, index=close.index, dtype=int)
    level = None
    for i in range(n):
        c = close.iloc[i]
        bs = brick_size.iloc[i]
        if pd.isna(bs) or bs <= 0 or pd.isna(c):
            continue
        if level is None:
            level = c
            continue
        if c >= level + bs:
            directions.iloc[i] = 1
            # advance level to the nearest brick boundary reached
            steps = int((c - level) // bs)
            level = level + steps * bs
        elif c <= level - bs:
            directions.iloc[i] = -1
            steps = int((level - c) // bs)
            level = level - steps * bs
    return directions


def generate_signals(
    price_df: pd.DataFrame,
    atr_window: int = 14,
    trend_window: int = 200,
    confirm_bricks: int = 2,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    brick_size = _atr(df, atr_window)
    brick_dir = _renko_bricks(close, brick_size)

    sma = close.rolling(trend_window).mean()
    above_trend = close > sma

    # forward-filled last brick direction (persists between brick-forming days)
    last_dir = brick_dir.replace(0, np.nan).ffill().fillna(0)
    # count consecutive days (bars) of the current direction persisting
    # (approximation of "N consecutive up-bricks" using the direction run length
    # since new bricks don't form every single day)
    dir_change = last_dir != last_dir.shift(1)
    run_id = dir_change.cumsum()
    run_length = last_dir.groupby(run_id).cumcount() + 1

    entry_trigger = (last_dir == 1) & (run_length >= confirm_bricks) & above_trend
    exit_trigger = (last_dir == -1) | (~above_trend)

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    for i in range(n):
        if in_pos:
            if bool(exit_trigger.iloc[i]):
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
                in_pos = True
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    atr_window: int = 14,
    trend_window: int = 200,
    confirm_bricks: int = 2,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df, atr_window=atr_window, trend_window=trend_window, confirm_bricks=confirm_bricks
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
