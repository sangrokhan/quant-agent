"""Strategy: STARC Bands lower-band-touch bullish reversal with bullish-candle
confirmation, exiting at the middle SMA or the opposite (upper) band.

Hypothesis (see knowledge_base id 2026-09-06-141):
Per forexbee.co's STARC Bands guide
(https://forexbee.co/starc-bands-indicator/): "A bullish trading strategy
revolves around the positive band of the STARC band indicator. When [price]
will reach the lower band or (starc -) then open a buy trade by analyzing
any bullish candlestick pattern... Take profit: partially close the trade
at the middle band and then close the rest of the trade when the price
touches the other opposite band."

STARC Bands (Manning Stoller): STARC+ = SMA(n) + multiplier*ATR(n),
STARC- = SMA(n) - multiplier*ATR(n). First STARC Bands strategy in this
repo -- distinct from prior Keltner Channel and Bollinger Band strategies
since STARC uses SMA+ATR (not EMA+ATR like Keltner, nor SMA+stdev like
Bollinger) and the source's specific two-target (middle-band partial, then
opposite-band full) exit logic rather than a single mean-reversion target.

Signal logic
------------
- STARC- (lower) band = SMA(sma_window) - atr_multiplier * ATR(atr_window).
- Entry (long): low of the bar touches/pierces STARC- (low <= STARC-),
  AND the bar closes bullish (close > open) as the source's "bullish
  candlestick pattern" confirmation (simplified to a single-bar close>open
  filter rather than a full candlestick-pattern library, since this repo's
  other candlestick strategies already implement specific named patterns
  elsewhere).
- Exit (simplified single-target version, since generate_signals returns a
  binary 0/1 position and can't do partial closes): close touches/exceeds
  the SMA midline (the source's first partial-profit target, taken here as
  the full exit to keep the position binary) OR a `max_hold_days` time-stop
  (source gives no explicit time-stop; added for robustness like other
  strategies in this repo).

Interface contract (see validation/validators.py, validation/grid_test.py):
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 15,
    atr_window: int = 15,
    atr_multiplier: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    low = df["low"]
    n = len(close)

    sma = close.rolling(sma_window).mean()
    atr = _atr(df, atr_window)
    starc_lower = sma - atr_multiplier * atr

    touch_lower = low <= starc_lower
    bullish_candle = close > open_
    entry = touch_lower & bullish_candle

    exit_midline = close >= sma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_midline.iloc[i]) or held >= max_hold_days:
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
