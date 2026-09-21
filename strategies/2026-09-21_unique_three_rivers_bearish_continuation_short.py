"""Strategy: Unique Three Rivers bearish continuation (short).

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration):
Per QuantifiedStrategies.com's "75 Types of Candlestick Patterns" list
(https://www.quantifiedstrategies.com/types-candlestick-patterns/, read via
browser_exec fallback -- web_extract ddgs backend cannot extract page
content), the "Unique Three Rivers" pattern is TRADITIONALLY classified as
a bullish reversal, but the source's OWN disclosed backtest finding is
that "it behaves more like a bearish continuation pattern on performance
tests" -- this strategy directly operationalizes the source's own
empirically-corrected reading (bearish continuation), not the traditional
textbook label, matching the source's exact stated pattern:
  - Bar1: a long black (bearish) candle in a downtrend.
  - Bar2: another black (bearish) candle with a long lower wick, that
    GAPS UP from bar1 but whose LOW is still BELOW bar1's low.
  - Bar3: a small bullish candle that lies entirely below bar2's body
    (i.e. bar3's high stays under bar2's body, a very weak/contained
    bounce attempt).
Source's own interpretation: bulls try to push the price up (bar3), but
bearish pressure is too strong since the highs constantly get lower with
every candlestick -- continuation lower expected.

First Unique Three Rivers entry in this repo (0 prior hits) -- distinct
from Three Black Crows (all 3 candles bearish, no gap-up/lower-wick
structure), Morning Star (bar2 is a small-bodied gap-down candle, not a
long-lower-wick bearish candle, and the overall pattern is a REVERSAL not
continuation), and this repo's other gap-based patterns (which all
require the SECOND candle to close near a prior extreme, not simply gap up
while making a lower low).

Signal logic
------------
- Downtrend filter: close[t-2] < close[t-2 - trend_lookback].
- Bar1 (t-2) long AND bearish: close[t-2] < open[t-2], body size >=
  long_body_mult * its own trailing atr_window-bar average true range.
- Bar2 (t-1) bearish: close[t-1] < open[t-1].
- Bar2 (t-1) gaps UP from bar1: open[t-1] > close[t-2].
- Bar2 (t-1) has a long lower wick: (min(open,close)[t-1] - low[t-1]) >=
  lower_wick_mult * body size of bar2.
- Bar2 (t-1) makes a LOWER LOW than bar1: low[t-1] < low[t-2].
- Bar3 (t) small AND bullish: close[t] > open[t], AND bar3's high stays
  below bar2's body: high[t] <= max(open,close)[t-1] * (1 + tolerance).
- No numeric stop/target disclosed by the source -- this repo's standard
  ATR stop/target and max-hold-days backstop used.
- Entry: short at bar t's own close once all of the above hold.
- Exit: close rises above its own SMA(exit_sma_window) OR the ATR
  target/stop is hit OR max_hold_days reached, whichever first.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 short-position
    flag, matching this repo's established short-strategy convention).
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
    trend_lookback: int = 10,
    long_body_mult: float = 1.0,
    atr_window: int = 20,
    lower_wick_mult: float = 1.0,
    tolerance: float = 0.005,
    exit_sma_window: int = 10,
    atr_stop_mult: float = 2.0,
    target_atr_mult: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} short-position-flag series (1 = actively short)."""
    df = _prep(price_df)
    idx = df.index
    n = len(idx)

    open_ = df["open"]
    close = df["close"]
    high = df["high"]
    low = df["low"]

    downtrend = close.shift(2) < close.shift(2 + trend_lookback)

    bar1_bearish = close.shift(2) < open_.shift(2)
    body1 = (open_.shift(2) - close.shift(2)).abs()
    true_range = (high - low).abs()
    avg_range = true_range.shift(3).rolling(atr_window).mean()
    bar1_long = body1 >= long_body_mult * avg_range.shift(2)

    bar2_bearish = close.shift(1) < open_.shift(1)
    bar2_gap_up = open_.shift(1) > close.shift(2)
    body2 = (open_.shift(1) - close.shift(1)).abs()
    min_oc2 = pd.concat([open_.shift(1), close.shift(1)], axis=1).min(axis=1)
    lower_wick2 = min_oc2 - low.shift(1)
    body2_safe = body2.replace(0, float("nan"))
    bar2_long_lower_wick = (lower_wick2 >= lower_wick_mult * body2_safe)
    bar2_lower_low = low.shift(1) < low.shift(2)

    bar3_bullish = close > open_
    max_oc2 = pd.concat([open_.shift(1), close.shift(1)], axis=1).max(axis=1)
    bar3_small_below = high <= max_oc2 * (1 + tolerance)

    pattern_confirmed = (
        downtrend.fillna(False)
        & bar1_bearish.fillna(False)
        & bar1_long.fillna(False)
        & bar2_bearish.fillna(False)
        & bar2_gap_up.fillna(False)
        & bar2_long_lower_wick.fillna(False)
        & bar2_lower_low.fillna(False)
        & bar3_bullish.fillna(False)
        & bar3_small_below.fillna(False)
    )

    atr = true_range.rolling(atr_window).mean()

    position = pd.Series(0, index=idx, dtype=int)
    stop_price = None
    target_price = None
    hold_count = 0

    confirmed = pattern_confirmed.to_numpy()
    close_arr = close.to_numpy()
    atr_arr = atr.to_numpy()
    sma_exit = close.rolling(exit_sma_window).mean().to_numpy()

    in_position = False
    for i in range(n):
        if in_position:
            hold_count += 1
            c = close_arr[i]
            exit_now = False
            if stop_price is not None and c >= stop_price:
                exit_now = True
            elif target_price is not None and c <= target_price:
                exit_now = True
            elif not pd.isna(sma_exit[i]) and c > sma_exit[i]:
                exit_now = True
            elif hold_count >= max_hold_days:
                exit_now = True
            if exit_now:
                in_position = False
                stop_price = target_price = None
                hold_count = 0
            else:
                position.iloc[i] = 1
                continue

        if not in_position and confirmed[i] and not pd.isna(atr_arr[i]) and atr_arr[i] > 0:
            in_position = True
            entry_price = close_arr[i]
            stop_price = entry_price + atr_stop_mult * atr_arr[i]
            target_price = entry_price - target_atr_mult * atr_arr[i]
            hold_count = 0
            position.iloc[i] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Daily strategy returns for a SHORT position: -1 * prior-day position
    * that day's simple return (position=1 means actively short)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **params)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = -1.0 * position.shift(1).fillna(0) * daily_ret
    return strat_ret
