"""Strategy: Moving Average Envelope mean-reversion (fixed-percentage bands).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-065):
Per RunBacktest's Moving Average Envelope Breakout page: draw upper/lower
envelope bands at a fixed percentage distance (envelope_pct, default 2%)
above/below an SMA(ma_window, default 20). This is a distinct calculation
basis from every prior band-based strategy in this repo (Bollinger/SD
channel use std-dev bands, Keltner uses ATR bands, VWAP bands use volume-
weighted variance) -- envelope bands are a simple fixed PERCENTAGE of the
moving average. Implementing the mean-reversion variant: long when close
touches/crosses below the lower envelope band, exit when price reverts
back to touch the middle SMA band.

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
    ma_window: int = 20,
    envelope_pct: float = 2.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(ma_window).mean()
    lower_band = sma * (1 - envelope_pct / 100.0)

    entry_signal = close <= lower_band
    exit_signal = close >= sma

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df)):
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
