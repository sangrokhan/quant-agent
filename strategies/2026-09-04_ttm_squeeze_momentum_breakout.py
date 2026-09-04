"""Strategy: TTM Squeeze (John Carter) -- Bollinger Bands inside Keltner
Channels detects a volatility squeeze; breakout with positive momentum
histogram direction signals a long entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-091):
When Bollinger Bands (20, 2 std) are fully contained WITHIN Keltner Channels
(20-EMA +/- keltner_mult*ATR(20)), volatility has compressed below its
"typical" range -- a squeeze. When the BB expands back outside the KC
("squeeze fires"), the following breakout tends to be directional; a
momentum histogram (here: linear-regression-style value = close minus the
average of a rolling high/low midpoint and the EMA, following John Carter's
original construction) determines breakout direction. Long entry when the
squeeze just fired AND momentum is positive; exit when momentum turns
negative or a squeeze re-forms.

Signal logic
------------
- squeeze_on[t]: upper_BB[t] <= upper_KC[t] AND lower_BB[t] >= lower_KC[t]
  (BB fully inside KC)
- squeeze_fired[t]: squeeze_on[t-1] == True AND squeeze_on[t] == False
  (squeeze just released)
- momentum[t]: close[t] - avg(rolling_donchian_mid[t], ema[t]), a simple
  proxy for Carter's linear-regression momentum histogram (direction +
  slope of price relative to its own recent range/trend midpoint)
- Entry: squeeze_fired[t] AND momentum[t] > 0
- Exit: momentum crosses below 0, OR a new squeeze forms (squeeze_on
  becomes True again while in position), OR max_hold_days elapsed

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window, min_periods=1).mean()


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    kc_window: int = 20,
    keltner_mult: float = 1.5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    sma = close.rolling(bb_window, min_periods=bb_window).mean()
    std = close.rolling(bb_window, min_periods=bb_window).std()
    upper_bb = sma + bb_std * std
    lower_bb = sma - bb_std * std

    ema = close.ewm(span=kc_window, adjust=False).mean()
    atr = _atr(df, kc_window)
    upper_kc = ema + keltner_mult * atr
    lower_kc = ema - keltner_mult * atr

    squeeze_on = (upper_bb <= upper_kc) & (lower_bb >= lower_kc)
    squeeze_on = squeeze_on.fillna(False)
    squeeze_fired = squeeze_on.shift(1).fillna(False) & (~squeeze_on)

    donchian_mid = (high.rolling(kc_window).max() + low.rolling(kc_window).min()) / 2.0
    momentum = close - (donchian_mid + ema) / 2.0

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_trigger = (
                bool(momentum.iloc[i] < 0)
                or bool(squeeze_on.iloc[i])
                or hold_count >= max_hold_days
            )
            if exit_trigger:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(squeeze_fired.iloc[i]) and bool(momentum.iloc[i] > 0):
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    kc_window: int = 20,
    keltner_mult: float = 1.5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        bb_window=bb_window,
        bb_std=bb_std,
        kc_window=kc_window,
        keltner_mult=keltner_mult,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
