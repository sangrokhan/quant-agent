"""Strategy: Bullish Trend Doji Star continuation (long).

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration):
Per QuantifiedStrategies.com's "75 Types of Candlestick Patterns" list
(https://www.quantifiedstrategies.com/types-candlestick-patterns/, read via
browser_exec fallback -- web_extract ddgs backend cannot extract page
content), the "Bullish Trend Doji Star" is a 2-candle CONTINUATION pattern
in an uptrend: bar1 is a tall bullish candle; bar2 is a doji that opens
with an UP-gap from bar1 (i.e. this is "an evening doji star that lacks
the vital third, bearish candle" -- the source's own framing). The
source's own interpretation: bulls continue to push the price higher, the
market hesitates (doji = brief pause), but bears do not win the battle --
i.e. this is a pause-then-continuation signal, NOT itself a reversal setup
(the reversal version, Evening Doji Star, requires the 3rd bearish
confirmation candle and is explicitly a DIFFERENT, already-distinguished
pattern per the source).

First Trend Doji Star entry in this repo (0 prior hits) -- distinct from
the already-tested Bullish Doji Star (2026-09-09-056, a 3-candle REVERSAL
pattern requiring bar1 BEARISH, then a doji, then a bullish breakout
candle -- structurally almost the mirror-opposite context: this pattern is
2-candle CONTINUATION in an existing uptrend with bar1 BULLISH, no 3rd
confirmation candle required by construction).

Signal logic
------------
- Uptrend filter: close[t-1] > close[t-1 - trend_lookback].
- Bar1 (t-1) tall AND bullish: close[t-1] > open[t-1], AND bar1's body
  size >= tall_body_mult * its own trailing atr_window-bar average true
  range (computed excluding bar1 itself to avoid leakage).
- Bar2 (t) is a doji: |close[t] - open[t]| <= doji_body_pct * (high[t] -
  low[t]) (small-or-no real body relative to its own range).
- Bar2 (t) gaps UP from bar1: open[t] > close[t-1] * (1 + min_gap_pct).
- No numeric stop/target disclosed by the source -- this repo's standard
  ATR stop/target and max-hold-days backstop used.
- Entry: long at bar t's own close once all of the above hold.
- Exit: close falls below its own SMA(exit_sma_window) (trend-reversal
  invalidates the continuation thesis) OR the ATR target/stop is hit OR
  max_hold_days reached, whichever first.

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
    tall_body_mult: float = 1.0,
    atr_window: int = 20,
    doji_body_pct: float = 0.10,
    min_gap_pct: float = 0.001,
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

    prior_close_shift = close.shift(trend_lookback)
    uptrend = close.shift(1) > prior_close_shift

    bar1_bullish = close.shift(1) > open_.shift(1)
    body1 = (close.shift(1) - open_.shift(1)).abs()
    true_range = (high - low).abs()
    avg_range = true_range.shift(2).rolling(atr_window).mean()
    bar1_tall = body1 >= tall_body_mult * avg_range.shift(1)

    bar2_range = (high - low).replace(0, pd.NA)
    bar2_body = (close - open_).abs()
    bar2_doji = (bar2_body / bar2_range) <= doji_body_pct

    bar2_up_gap = open_ > close.shift(1) * (1 + min_gap_pct)

    pattern_confirmed = (
        uptrend.fillna(False)
        & bar1_bullish.fillna(False)
        & bar1_tall.fillna(False)
        & bar2_doji.fillna(False)
        & bar2_up_gap.fillna(False)
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
