"""Strategy: Three Inside Up candlestick reversal, breakout-distance + volume
confirmation, fixed time exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-182):
The Three Inside Up is a classic 3-bar bullish reversal candlestick pattern:
(1) a bearish candle continuing a prior downtrend, (2) an "inside bar" whose
full range sits inside candle 1's body, (3) a bullish candle closing above
the high of the pattern (candles 1+2). Per QuantifiedStrategies.com's Three
Inside Up guide, the raw pattern is not tradeable on its own -- two concrete
filters are disclosed: (a) require the breakout close to clear the pattern
high by an extra buffer of half the Average True Range (mitigates false
breakouts) and/or (b) require above-average volume on the breakout candle
(confirms genuine buying conviction, not a low-conviction drift). Both
source variants exit after a fixed 5-bar hold. This repo combines both
filters (breakout distance AND volume confirmation) rather than testing
them singly, and adds an RSI oversold gate (source's own suggested
"oversold conditions" enhancement, RSI<30) as an optional additional filter
to test whether combining all three disclosed enhancements improves on the
single-filter variants. First Three Inside Up (or any 3-bar OHLC candlestick
reversal, as opposed to 2-bar Bullish Kicker id=2026-09-06-155) strategy in
this repo.

Signal logic
------------
- Candle 1 (2 bars ago): bearish (close < open).
- Candle 2 (1 bar ago): "inside bar" -- its high <= candle 1's high AND its
  low >= candle 1's low.
- Candle 3 (today): bullish (close > open) AND closes above
  (pattern_high + breakout_atr_mult * ATR(atr_window)), where pattern_high =
  max(candle1.high, candle2.high).
- Volume filter: candle 3's volume >= vol_mult * rolling vol_window-day
  average volume (computed prior to today).
- Optional oversold gate: RSI(rsi_window) on the close *before* the pattern
  (2 bars ago) <= rsi_oversold (set rsi_oversold=100 to effectively disable
  this filter).
- Entry: long at candle 3's close when all of the above hold.
- Exit: fixed hold_bars trading days after entry (source's own "wait for 5
  bars to exit" rule), no early exit condition disclosed by the source.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, atr_window: int) -> pd.Series:
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
    return tr.rolling(atr_window).mean()


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    atr_window: int = 14,
    breakout_atr_mult: float = 0.5,
    vol_window: int = 20,
    vol_mult: float = 1.2,
    rsi_window: int = 14,
    rsi_oversold: float = 40.0,
    hold_bars: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    open_, high, low, close, volume = (
        df["open"], df["high"], df["low"], df["close"], df["volume"]
    )

    bearish1 = (close.shift(2) < open_.shift(2))
    inside2 = (high.shift(1) <= high.shift(2)) & (low.shift(1) >= low.shift(2))
    bullish3 = close > open_

    pattern_high = pd.concat([high.shift(2), high.shift(1)], axis=1).max(axis=1)
    atr = _atr(df, atr_window)
    breakout_level = pattern_high + breakout_atr_mult * atr

    avg_vol = volume.rolling(vol_window).mean().shift(1)
    vol_ok = volume >= (vol_mult * avg_vol)

    rsi = _rsi(close, rsi_window)
    oversold_ok = rsi.shift(2) <= rsi_oversold

    entry = bearish1 & inside2 & bullish3 & (close > breakout_level) & vol_ok & oversold_ok
    entry = entry.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= hold_bars:
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
