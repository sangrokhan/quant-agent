"""Strategy: Three Stars In The South bullish reversal (long).

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration):
Per QuantifiedStrategies.com (https://www.quantifiedstrategies.com/three-stars-in-the-south-candlestick-pattern/,
read via browser_exec fallback -- web_extract ddgs backend cannot extract
page content) and corroborated by Bulkowski's own ranking (per Google
search snippet from thepatternsite.com: "ranks first, yes, first, for
reversal performance"), Three Stars In The South is a rare 3-candle
bullish reversal pattern in a downtrend, made up of three consecutive
BEARISH candles with progressively shrinking, nested ranges (each
candle's high-low range is completely covered by the preceding candle's
range -- "an inside bar within an inside bar"):
  - Bar1: a long bearish candle with a long lower shadow.
  - Bar2: a smaller bearish candle with a HIGHER low and a LOWER high
    than bar1 (nested inside bar1's range).
  - Bar3: a small black Marubozu (near-zero wicks) that starts and ends
    entirely within bar2's range (nested inside bar2's range).
Source's own interpretation: diminishing daily ranges + consecutively
higher lows despite each close being lower than the last = the downtrend
is losing momentum even though price nominally keeps falling; bulls
expected to step in soon.

First Three Stars In The South entry in this repo (0 prior hits) --
explicitly distinct from Three Black Crows (per the source's own stated
distinction: Three Black Crows candles are each progressively LARGER/
extending the range, the opposite of this pattern's progressively
SHRINKING nested-inside-bar structure).

Signal logic
------------
- Downtrend filter: close[t-2] < close[t-2 - trend_lookback].
- Bar1 (t-2) bearish with a long lower shadow: close[t-2] < open[t-2], AND
  (min(open,close)[t-2] - low[t-2]) >= lower_wick_mult * body size of bar1.
- Bar2 (t-1) bearish, nested inside bar1: close[t-1] < open[t-1], AND
  high[t-1] < high[t-2], AND low[t-1] > low[t-2].
- Bar3 (t) a small black Marubozu nested inside bar2: close[t] < open[t],
  AND high[t] <= open[t] * (1 + marubozu_wick_pct) (near-zero upper
  wick), AND low[t] >= close[t] * (1 - marubozu_wick_pct) (near-zero
  lower wick), AND high[t] <= high[t-1] AND low[t] >= low[t-1].
- No numeric stop/target disclosed by the source -- this repo's standard
  ATR stop/target and max-hold-days backstop used.
- Entry: long at bar t's own close once all of the above hold.
- Exit: close falls below its own SMA(exit_sma_window) OR the ATR
  target/stop is hit OR max_hold_days reached, whichever first.

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


def generate_signals(
    price_df: pd.DataFrame,
    trend_lookback: int = 10,
    lower_wick_mult: float = 0.5,
    marubozu_wick_pct: float = 0.005,
    atr_window: int = 20,
    exit_sma_window: int = 10,
    atr_stop_mult: float = 2.0,
    target_atr_mult: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
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
    min_oc1 = pd.concat([open_.shift(2), close.shift(2)], axis=1).min(axis=1)
    lower_wick1 = min_oc1 - low.shift(2)
    body1_safe = body1.replace(0, float("nan"))
    bar1_long_lower_wick = lower_wick1 >= lower_wick_mult * body1_safe

    bar2_bearish = close.shift(1) < open_.shift(1)
    bar2_nested = (high.shift(1) < high.shift(2)) & (low.shift(1) > low.shift(2))

    bar3_bearish = close < open_
    bar3_marubozu = (high <= open_ * (1 + marubozu_wick_pct)) & (
        low >= close * (1 - marubozu_wick_pct)
    )
    bar3_nested = (high <= high.shift(1)) & (low >= low.shift(1))

    pattern_confirmed = (
        downtrend.fillna(False)
        & bar1_bearish.fillna(False)
        & bar1_long_lower_wick.fillna(False)
        & bar2_bearish.fillna(False)
        & bar2_nested.fillna(False)
        & bar3_bearish.fillna(False)
        & bar3_marubozu.fillna(False)
        & bar3_nested.fillna(False)
    )

    true_range = (high - low).abs()
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
            if stop_price is not None and c <= stop_price:
                exit_now = True
            elif target_price is not None and c >= target_price:
                exit_now = True
            elif not pd.isna(sma_exit[i]) and c < sma_exit[i]:
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
            stop_price = entry_price - atr_stop_mult * atr_arr[i]
            target_price = entry_price + target_atr_mult * atr_arr[i]
            hold_count = 0
            position.iloc[i] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **params)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
