"""Strategy: Bullish Deliberation (Stalled) Pattern continuation long.

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration):
Per QuantifiedStrategies.com's "75 Types of Candlestick Patterns" list
(https://www.quantifiedstrategies.com/types-candlestick-patterns/, read via
browser_exec fallback -- web_extract ddgs backend cannot extract page
content), the "Deliberation" (aka "Stalled") pattern is TRADITIONALLY
classified as a bearish reversal signal, but the source's OWN disclosed
finding is that it "tends to be followed by a rising market more often
than not." This strategy directly operationalizes the source's own
empirically-corrected reading (bullish continuation), matching the
source's exact stated identification rule:
  - Three consecutive bullish candles in an uptrend.
  - The first and second candles have tall bodies; the third has a small
    body (the "hesitation" bar the pattern is named for).
  - Each candle's open and close prices are higher than the preceding
    one (a strictly ascending staircase of opens/closes).
Source's own interpretation: buyers were initially enthusiastic but later
started having doubts (the small 3rd candle); however sellers are too
scared to press the advantage (no lower close on bar3), so buyers resume
soon after -- i.e. this is a brief-pause-then-continuation signal, exactly
matching this repo's already-established pattern for several other
"pause candle in a strong trend" strategies (e.g. Bullish Trend Doji Star,
this cron trigger's earlier iteration), but using a SMALL-BODY bullish
3rd candle rather than a doji.

First Deliberation/Stalled entry in this repo (0 prior hits) -- distinct
from Rising Three Methods (which requires 3-4 BEARISH middle candles that
retrace but don't break the first candle's low, a materially different
mid-pattern structure) and Three White Soldiers (which requires all THREE
candles to be tall, not a tall-tall-small structure).

Signal logic
------------
- Uptrend filter: close[t-3] > close[t-3 - trend_lookback].
- Bar1 (t-2), Bar2 (t-1): both bullish (close>open) AND tall (body size
  >= tall_body_mult * trailing atr_window-bar average true range,
  computed excluding the pattern bars themselves).
- Bar3 (t): bullish AND small (body size <= small_body_mult * the same
  trailing average true range).
- Ascending staircase: open[t-1]>open[t-2], close[t-1]>close[t-2],
  open[t]>open[t-1], close[t]>close[t-1].
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
    tall_body_mult: float = 1.0,
    small_body_mult: float = 0.5,
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

    uptrend = close.shift(3) > close.shift(3 + trend_lookback)

    bar1_bullish = close.shift(2) > open_.shift(2)
    bar2_bullish = close.shift(1) > open_.shift(1)
    bar3_bullish = close > open_

    true_range = (high - low).abs()
    avg_range = true_range.shift(3).rolling(atr_window).mean()

    body1 = (close.shift(2) - open_.shift(2)).abs()
    body2 = (close.shift(1) - open_.shift(1)).abs()
    body3 = (close - open_).abs()

    bar1_tall = body1 >= tall_body_mult * avg_range.shift(2)
    bar2_tall = body2 >= tall_body_mult * avg_range.shift(1)
    bar3_small = body3 <= small_body_mult * avg_range

    ascending = (
        (open_.shift(1) > open_.shift(2))
        & (close.shift(1) > close.shift(2))
        & (open_ > open_.shift(1))
        & (close > close.shift(1))
    )

    pattern_confirmed = (
        uptrend.fillna(False)
        & bar1_bullish.fillna(False)
        & bar2_bullish.fillna(False)
        & bar3_bullish.fillna(False)
        & bar1_tall.fillna(False)
        & bar2_tall.fillna(False)
        & bar3_small.fillna(False)
        & ascending.fillna(False)
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
