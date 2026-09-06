"""Strategy: Morning Star three-candle bullish reversal pattern, trend-gated, long-only.

Hypothesis (see knowledge_base id 2026-09-06-161):
Per QuantifiedStrategies.com's Morning Star candlestick backtest article
(https://www.quantifiedstrategies.com/morning-star-candlestick-pattern/):
the Morning Star is a three-candle bullish reversal pattern:
  - Candle 1: a tall bearish candle (close < open, large body) in line with
    the ongoing downswing.
  - Candle 2: a small-bodied candle (doji/spinning-top) that gaps DOWN from
    candle 1 (candle 2's high is below candle 1's low, or at minimum its
    body sits below candle 1's close) -- signaling indecision.
  - Candle 3: a bullish candle that opens below candle 2 and closes above
    the MIDPOINT of candle 1's body (source: "engulfs the second candle and
    pierces the first candle").
The pattern should appear "at the bottom of a downtrend or a downward price
swing" (source's own precondition) -- operationalized here, consistent with
every other candlestick strategy in this repo, as close < SMA(trend_window)
as of candle 1.

First Morning Star strategy in this repo -- distinct from every other
single/dual-candle pattern already tested (Hammer 2026-09-06-147: single
candle, long lower wick; Piercing Line: two-candle midpoint-cross; Bullish
Harami: two-candle contained-body; Bullish Engulfing: two-candle full-body
overtake; Bullish Kicker: two-candle gap-above-open; Tweezer Bottom:
two-candle matching-lows; Three White Soldiers: three consecutive bullish
candles, no gap-down middle candle) -- Morning Star's defining feature is
the specific THREE-candle bearish -> small-gap-down -> bullish-piercing
sequence.

Signal logic
------------
- Candle 1 (index i-2): bearish (close < open), body size above the median
  body size over `trend_window` bars (source's "tall bearish candle"),
  AND close < SMA(trend_window) (downtrend precondition).
- Candle 2 (index i-1): small body relative to candle 1
  (body_2 <= small_body_ratio * body_1), AND gaps down from candle 1
  (candle 2's high <= candle 1's low, per source's "gaps below the first
  candlestick").
- Candle 3 (index i, today): bullish (close > open), opens below candle 2's
  close (source: "opens below the second candle"), AND closes above candle
  1's midpoint ((open_1 + close_1) / 2, source's "closes above the midpoint
  of the first candle").
- Entry: long at today's (candle 3's) close, consistent with this repo's
  shift(1) execution-lag convention.
- Exit: close crossing back below candle 1's low (pattern invalidated), OR
  a `max_hold_days` time-stop.

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
    trend_window: int = 50,
    small_body_ratio: float = 0.5,
    max_hold_days: int = 12,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]
    n = len(close)

    body = (close - open_).abs()
    is_bearish = close < open_
    is_bullish = close > open_

    sma = close.rolling(trend_window).mean()
    downtrend = close < sma
    body_median = body.rolling(trend_window).median()

    # Candle 1 = shift(2), candle 2 = shift(1), candle 3 = today.
    c1_bearish = is_bearish.shift(2)
    c1_body = body.shift(2)
    c1_tall = c1_body >= body_median.shift(2)
    c1_downtrend = downtrend.shift(2)
    c1_low = low.shift(2)
    c1_open = open_.shift(2)
    c1_close = close.shift(2)
    c1_midpoint = (c1_open + c1_close) / 2.0

    c2_body = body.shift(1)
    c2_high = high.shift(1)
    c2_close = close.shift(1)
    c2_small = c2_body <= (small_body_ratio * c1_body)
    c2_gap_down = c2_high <= c1_low

    c3_bullish = is_bullish
    c3_opens_below_c2 = open_ < c2_close
    c3_closes_above_c1_mid = close > c1_midpoint

    entry = (
        c1_bearish.fillna(False)
        & c1_tall.fillna(False)
        & c1_downtrend.fillna(False)
        & c2_small.fillna(False)
        & c2_gap_down.fillna(False)
        & c3_bullish.fillna(False)
        & c3_opens_below_c2.fillna(False)
        & c3_closes_above_c1_mid.fillna(False)
    )

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    pattern_low = np.nan

    for i in range(n):
        if in_position:
            held = i - entry_idx
            stop_hit = (not np.isnan(pattern_low)) and (close.iloc[i] < pattern_low)
            if stop_hit or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                pattern_low = np.nan
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                pattern_low = c1_low.iloc[i]
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
