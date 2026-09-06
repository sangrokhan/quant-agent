"""Strategy: Trade Volume Index (TVI) rising + RSI-not-overbought confirmation
long entry.

Hypothesis (see knowledge_base id 2026-09-06-142):
Per timothysykes.com's TVI guide
(https://www.timothysykes.com/blog/how-to-use-trade-volume-index/):
"If the TVI shows strong buying pressure and the RSI indicates that a stock
is not yet overbought, it could be a signal to enter a [trade]." Also:
"a downtrend supported by a declining TVI suggests that selling pressure is
driving the market lower... a stock is trending upward and the TVI is
increasing, it confirms that the trend is backed by strong buying
activity."

Trade Volume Index (William Blau's classic definition): a cumulative
volume-flow line that adds today's volume when price rises by more than a
minimum tick threshold, subtracts it when price falls by more than that
threshold, and otherwise repeats the prior day's direction (keeps the
running total moving the same way as the last confirmed move) -- distinct
from On-Balance Volume (which uses a plain close>close-yesterday test with
no minimum-move threshold) and from the Accumulation/Distribution Line
(which weights volume by intrabar close-location, not day-over-day price
direction). First TVI strategy in this repo.

Signal logic
------------
- TVI: cumulative sum where day t's signed volume contribution is
  +volume_t if close_t - close_{t-1} > min_tick, -volume_t if
  close_t - close_{t-1} < -min_tick, else repeat yesterday's sign
  (Blau's rule; `min_tick` expressed as a fraction of price, default 0.1%).
- TVI trend: `tvi_sma_window`-day SMA of TVI is rising (today's TVI SMA >
  TVI SMA `tvi_slope_lookback` days ago) -- the "TVI increasing" trend
  confirmation from the source.
- RSI: standard Wilder RSI(`rsi_window`).
- Entry (long): TVI trend is rising AND RSI is below `rsi_overbought`
  (source's "not yet overbought" condition) AND price is above its
  `price_trend_sma_window`-day SMA (source's "stock is trending upward"
  precondition for using TVI as trend confirmation, not a standalone
  signal).
- Exit: RSI crosses above `rsi_overbought`, OR TVI trend flips down, OR a
  `max_hold_days` time-stop.

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


def _tvi(close: pd.Series, volume: pd.Series, min_tick_pct: float) -> pd.Series:
    n = len(close)
    tvi = np.zeros(n)
    last_dir = 1.0
    for i in range(1, n):
        change = close.iloc[i] - close.iloc[i - 1]
        threshold = min_tick_pct * close.iloc[i - 1]
        if change > threshold:
            direction = 1.0
        elif change < -threshold:
            direction = -1.0
        else:
            direction = last_dir
        tvi[i] = tvi[i - 1] + direction * volume.iloc[i]
        last_dir = direction
    return pd.Series(tvi, index=close.index)


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    min_tick_pct: float = 0.001,
    tvi_sma_window: int = 10,
    tvi_slope_lookback: int = 5,
    rsi_window: int = 14,
    rsi_overbought: float = 65.0,
    price_trend_sma_window: int = 50,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]
    n = len(close)

    tvi = _tvi(close, volume, min_tick_pct)
    tvi_sma = tvi.rolling(tvi_sma_window).mean()
    tvi_rising = tvi_sma > tvi_sma.shift(tvi_slope_lookback)

    rsi = _rsi(close, rsi_window)
    not_overbought = rsi < rsi_overbought

    price_trend_sma = close.rolling(price_trend_sma_window).mean()
    price_uptrend = close > price_trend_sma

    entry = tvi_rising.fillna(False) & not_overbought.fillna(False) & price_uptrend.fillna(False)
    exit_overbought = rsi >= rsi_overbought
    exit_tvi_flip = ~tvi_rising.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_overbought.iloc[i]) or bool(exit_tvi_flip.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
