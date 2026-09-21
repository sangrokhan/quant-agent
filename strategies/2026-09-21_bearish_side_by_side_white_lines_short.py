"""Strategy: Bearish Side by Side White Lines continuation (short).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-275):
Per QuantifiedStrategies.com's "75 Types of Candlestick Patterns"
(https://www.quantifiedstrategies.com/types-candlestick-patterns/, same
source already used in this repo for Unique Three Rivers and Upside Gap
Two Crows), the "Bearish Side by Side White Lines" pattern is a
3-candlestick BEARISH CONTINUATION pattern occurring in a downtrend:
bar1 is a tall bearish candle, bar2 is a smaller bullish candle that opens
with a DOWN gap from bar1 (open[t-1] < close[t-2]), and bar3 is a second
bullish candle similar in size to bar2 that opens close to bar2's own open
(within a tolerance). Source's own interpretation: "Sellers were very
aggressive, as indicated by the tall bearish first candle and the gap.
Bulls fought back but despite their best effort, they couldn't overcome
the bears" -- i.e. the two failed bullish attempts (bar2, bar3) confirm
downtrend continuation is likely. First Side-by-Side-White-Lines entry in
this repo (0 prior hits) -- distinct from Falling Three Methods (5 candles,
requires the small candles to stay below bar1's high, not specifically
gap down and open near each other) and from the already-tested Separating
Lines (2-candle, requires matching OPEN prices not gap-down + similar
opens on the SECOND and THIRD candles).

Signal logic
------------
- Downtrend filter: close[t-2] < close[t-2 - trend_lookback].
- Bar1 (t-2): tall bearish candle -- close[t-2] < open[t-2], body size >=
  long_body_mult * its own trailing atr_window-bar average true range.
- Bar2 (t-1): bullish candle -- close[t-1] > open[t-1] -- that gaps DOWN
  from bar1: open[t-1] < close[t-2] * (1 - gap_tolerance).
- Bar3 (t): bullish candle -- close[t] > open[t] -- whose open is close to
  bar2's own open (within open_similarity_tolerance, relative to bar2's
  own range), the "side by side" defining feature.
- Entry: short at bar3's own close once all of the above hold (source's
  own bearish-continuation reading of the completed 3-bar pattern).
- Exit: close crosses back above bar1's own open (source's implied "bulls
  overcame the bears" invalidation level) OR max_hold_days reached,
  whichever comes first.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position series)
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
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    trend_lookback: int = 10,
    long_body_mult: float = 0.7,
    gap_tolerance: float = 0.002,
    open_similarity_tolerance: float = 0.015,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} short/flat position series (1 == short exposure)."""
    df = _prep(price_df)
    idx = df.index
    n = len(idx)

    open_ = df["open"]
    close = df["close"]

    atr = _atr(df, atr_window := 14)
    body = (close - open_).abs()

    downtrend = close.shift(2) < close.shift(2 + trend_lookback)

    bar1_bearish_tall = (close.shift(2) < open_.shift(2)) & (body.shift(2) >= long_body_mult * atr.shift(2))
    bar2_bullish = close.shift(1) > open_.shift(1)
    bar2_gap_down = open_.shift(1) < close.shift(2) * (1 - gap_tolerance)
    bar3_bullish = close > open_
    bar3_open_similar_to_bar2_open = (
        (open_ - open_.shift(1)).abs() <= open_similarity_tolerance * open_.shift(1)
    )

    entry_signal = (
        downtrend
        & bar1_bearish_tall
        & bar2_bullish
        & bar2_gap_down
        & bar3_bullish
        & bar3_open_similar_to_bar2_open
    ).fillna(False)

    invalidation_level = open_.shift(2).where(entry_signal).ffill()

    position = pd.Series(0, index=idx, dtype=int)
    in_pos = False
    hold_bars = 0
    inv_level = None
    for i in range(n):
        if in_pos:
            hold_bars += 1
            if close.iloc[i] > inv_level or hold_bars >= max_hold_days:
                in_pos = False
                hold_bars = 0
                inv_level = None
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_pos = True
                hold_bars = 0
                inv_level = open_.shift(2).iloc[i]
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_lookback: int = 10,
    long_body_mult: float = 0.7,
    gap_tolerance: float = 0.002,
    open_similarity_tolerance: float = 0.015,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs).
    Position=1 means SHORT exposure (inverse daily return).
    """
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        trend_lookback=trend_lookback,
        long_body_mult=long_body_mult,
        gap_tolerance=gap_tolerance,
        open_similarity_tolerance=open_similarity_tolerance,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = -daily_ret * position.shift(1).fillna(0)
    return strat_ret
