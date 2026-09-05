"""Strategy: SuperTrend + RSI dual-confirmation trend following, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-095),
sourced from FMZ.com's "RSI and SuperTrend Based Dual Direction Trading
Strategy" (Google search snippet: "Go long when RSI goes above 50 and
price breaks above SuperTrend upper band. Go short when RSI falls below
50 and price breaks below lower band.").

This repo already tested plain SuperTrend flip strategies (2026-09-03-014,
rejected; 2026-09-04-053, accepted QQQ+SPY, ATR period=10/multiplier=3)
with NO RSI gate. This variant is distinct: it requires RSI>50
(bullish-momentum confirmation) SIMULTANEOUSLY with the SuperTrend
bullish flip -- screening out SuperTrend flips that occur without
underlying momentum backing them, which should reduce false starts /
whipsaw entries relative to the plain SuperTrend baseline.

Signal logic
------------
- SuperTrend: ATR(atr_period)-based band around HL2, multiplier
  atr_multiplier, standard flip/carry-forward state machine.
- RSI(rsi_window) on close.
- Long entry: SuperTrend flips bullish (price crosses above the
  SuperTrend line, i.e. trend direction switches from down to up) AND
  RSI > rsi_threshold (50, source's exact rule) at that bar.
- Exit: SuperTrend flips bearish (price crosses below), or a
  max_hold_days time-stop (repo standard safety valve).

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


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    tr = _true_range(df)
    return tr.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _supertrend_direction(df: pd.DataFrame, atr_period: int, atr_multiplier: float) -> pd.Series:
    """Return a {-1,1} series: 1 = bullish (price above SuperTrend line),
    -1 = bearish (price below), standard flip-and-carry-forward state
    machine."""
    high, low, close = df["high"], df["low"], df["close"]
    hl2 = (high + low) / 2.0
    atr = _atr(df, atr_period)

    upper_basic = hl2 + atr_multiplier * atr
    lower_basic = hl2 - atr_multiplier * atr

    n = len(df)
    final_upper = np.full(n, np.nan)
    final_lower = np.full(n, np.nan)
    direction = np.ones(n, dtype=int)

    ub = upper_basic.values
    lb = lower_basic.values
    c = close.values

    for i in range(n):
        if i == 0 or np.isnan(ub[i - 1]):
            final_upper[i] = ub[i]
            final_lower[i] = lb[i]
            direction[i] = 1
            continue

        final_upper[i] = ub[i] if (ub[i] < final_upper[i - 1] or c[i - 1] > final_upper[i - 1]) else final_upper[i - 1]
        final_lower[i] = lb[i] if (lb[i] > final_lower[i - 1] or c[i - 1] < final_lower[i - 1]) else final_lower[i - 1]

        if direction[i - 1] == 1:
            direction[i] = -1 if c[i] < final_lower[i] else 1
        else:
            direction[i] = 1 if c[i] > final_upper[i] else -1

    return pd.Series(direction, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    atr_period: int = 10,
    atr_multiplier: float = 3.0,
    rsi_window: int = 14,
    rsi_threshold: float = 50.0,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    direction = _supertrend_direction(df, atr_period, atr_multiplier)
    rsi = _rsi(close, rsi_window)

    bullish_flip = (direction == 1) & (direction.shift(1) == -1)
    bearish_flip = (direction == -1) & (direction.shift(1) == 1)

    entry_signal = (bullish_flip & (rsi > rsi_threshold)).fillna(False).values
    exit_signal = bearish_flip.fillna(False).values

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0

    for i in range(len(df.index)):
        if in_position:
            hold_count += 1
            if exit_signal[i] or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_signal[i]:
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
