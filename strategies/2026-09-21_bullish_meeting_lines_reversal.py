"""Strategy: Bullish Meeting Lines reversal (long).

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration):
Per QuantifiedStrategies.com's "75 Types of Candlestick Patterns" list
(https://www.quantifiedstrategies.com/types-candlestick-patterns/, read via
browser_exec fallback -- web_extract ddgs backend cannot extract page
content), the "Bullish Meeting Lines" pattern is a 2-candle bullish
REVERSAL pattern in a downtrend: bar1 is bearish, bar2 is a full positive
(bullish) candle that opens with a down-gap but rallies to close very near
bar1's close (the two candles' closes "meet").

Distinct from every other close-matching candlestick pattern already
tested in this repo:
  - Matching Low (2026-09-21-219): bar2 is also BEARISH (both candles
    bearish, matching CLOSES despite a small gap UP -- a continuation-by-
    default pattern requiring a separate confirmation candle); here bar2
    is a full BULLISH candle and the reversal is the pattern itself.
  - In Neck Line (2026-09-21-240): a bearish CONTINUATION pattern (bar2's
    small rally fails to overcome bar1); Meeting Lines' bar2 is
    unambiguously a full positive candle, not a failed small rally.
  - On Neck Line: bar2 closes at bar1's LOW, not bar1's CLOSE.
  - Piercing Pattern: bar2 closes ABOVE the MIDPOINT of bar1's body (a
    materially deeper penetration than "closes near bar1's close").

First Meeting Lines entry in this repo (0 prior hits).

Signal logic
------------
- Downtrend filter: close[t-1] < close[t-1 - trend_lookback].
- Bar1 (t-1) bearish: close[t-1] < open[t-1].
- Bar2 (t) opens with a down-gap: open[t] < close[t-1].
- Bar2 (t) is a full bullish candle: close[t] > open[t].
- Bar2's close matches bar1's close (the defining "meeting"):
  |close[t] - close[t-1]| <= match_tolerance * close[t-1].
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
    match_tolerance: float = 0.005,
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

    prior_close_shift = close.shift(trend_lookback)
    downtrend = close.shift(1) < prior_close_shift

    bar1_bearish = close.shift(1) < open_.shift(1)
    bar2_down_gap = open_ < close.shift(1)
    bar2_bullish = close > open_
    bar2_meets_close = (close - close.shift(1)).abs() <= match_tolerance * close.shift(1).abs()

    pattern_confirmed = (
        downtrend.fillna(False)
        & bar1_bearish.fillna(False)
        & bar2_down_gap.fillna(False)
        & bar2_bullish.fillna(False)
        & bar2_meets_close.fillna(False)
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
