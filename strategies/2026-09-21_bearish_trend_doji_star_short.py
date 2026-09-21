"""Strategy: Bearish Trend Doji Star continuation (short).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-276):
Per QuantifiedStrategies.com's "75 Types of Candlestick Patterns"
(https://www.quantifiedstrategies.com/types-candlestick-patterns/, same
source used for this repo's Unique Three Rivers/Upside Gap Two
Crows/Side-by-Side-White-Lines entries), the "Bearish Trend Doji Star" is
a 2-candlestick continuation pattern that forms in a downtrend: bar1 is a
tall bearish candle, bar2 is a doji (near-zero real body) that opens with
a down gap from bar1. Source's own reasoning: the selling pressure in
bar1 pushed price down; bar2 (the doji) shows bears pausing, but as long
as NO bullish confirmation candle follows (which would instead form a
"morning doji star" reversal, already implicitly covered by this repo's
existing morning-star-family entries), the downtrend is likely to
continue. This strategy operationalizes the "no confirmation candle"
continuation reading directly: entry triggers if the bar immediately
after the doji is NOT strongly bullish (closing back below the doji's own
high, i.e. failing to confirm a reversal). First Bearish Trend Doji Star
entry in this repo (0 prior hits) -- distinct from Morning/Evening Doji
Star (3-candle REVERSAL pattern requiring an explicit bullish/bearish
confirmation candle) since this pattern is defined by the ABSENCE of that
confirmation.

Signal logic
------------
- Downtrend filter: close[t-2] < close[t-2 - trend_lookback].
- Bar1 (t-2): tall bearish candle -- close[t-2] < open[t-2], body size >=
  long_body_mult * its own trailing atr_window-bar average true range.
- Bar2 (t-1): doji -- real body size <= doji_body_ratio * bar2's own
  high-low range -- that gaps DOWN from bar1: max(open,close)[t-1] <
  close[t-2] * (1 - gap_tolerance).
- Bar3 (t): NOT a bullish confirmation candle -- close[t] <= high[t-1]
  (fails to close above the doji's own high, i.e. no reversal
  confirmation).
- Entry: short at bar3's own close once all of the above hold (source's
  "downtrend likely to continue" reading when no confirmation follows).
- Exit: close crosses back above bar1's own open (structural invalidation
  level, consistent with this repo's other bearish-continuation
  candlestick strategies) OR max_hold_days reached, whichever comes
  first.

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
    doji_body_ratio: float = 0.1,
    gap_tolerance: float = 0.001,
    atr_window: int = 14,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} short/flat position series (1 == short exposure)."""
    df = _prep(price_df)
    idx = df.index
    n = len(idx)

    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]

    atr = _atr(df, atr_window)
    body = (close - open_).abs()
    rng = (high - low).replace(0.0, float("nan"))

    downtrend = close.shift(2) < close.shift(2 + trend_lookback)

    bar1_bearish_tall = (close.shift(2) < open_.shift(2)) & (body.shift(2) >= long_body_mult * atr.shift(2))

    doji_body_ratio_bar2 = body.shift(1) / rng.shift(1)
    bar2_doji = doji_body_ratio_bar2 <= doji_body_ratio
    bar2_top = pd.concat([open_.shift(1), close.shift(1)], axis=1).max(axis=1)
    bar2_gap_down = bar2_top < close.shift(2) * (1 - gap_tolerance)

    bar3_no_confirmation = close <= high.shift(1)

    entry_signal = (
        downtrend
        & bar1_bearish_tall
        & bar2_doji
        & bar2_gap_down
        & bar3_no_confirmation
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
    doji_body_ratio: float = 0.1,
    gap_tolerance: float = 0.001,
    atr_window: int = 14,
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
        doji_body_ratio=doji_body_ratio,
        gap_tolerance=gap_tolerance,
        atr_window=atr_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = -daily_ret * position.shift(1).fillna(0)
    return strat_ret
