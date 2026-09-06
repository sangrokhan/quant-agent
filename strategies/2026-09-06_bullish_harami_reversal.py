"""Strategy: Bullish Harami reversal (2-candle pattern), downtrend-gated,
long-only.

Hypothesis (see knowledge_base id 2026-09-06-149):
Per TradingView's "Candlestick Patterns" script description
(https://www.tradingview.com/scripts/hammer/, already used for the
already-tested Hammer 2026-09-06-147 and Piercing Line 2026-09-06-148
strategies): "Harami requires the current body to fit inside the prior
range and be less than 60% of the prior body size." Per Dukascopy's Harami
guide (Google SERP): "Bullish Haramis (large bearish candle followed by
smaller bullish candle) suggest upward reversals during downtrends." Per
LiteFinance's guide (Google SERP): "it is advisable to set a stop-loss order
just below the pattern's low."

First Harami-pattern strategy in this repo -- distinct from Piercing Line
(2026-09-06-148, requires a gap-down open and a MIDPOINT cross, i.e. Day2's
body extends beyond Day1's midpoint) and Bullish Engulfing (2026-09-04-102,
Day2's body fully ENGULFS Day1's, i.e. LARGER not smaller): Harami is
defined by Day2's body being small and entirely CONTAINED inside Day1's
larger body -- essentially the opposite size relationship from Engulfing.

Signal logic
------------
- Day 1 (bearish setup candle): close < open (large bearish body), occurring
  in a confirmed downtrend (close < SMA(trend_window)).
- Day 2 (harami candle): close > open (bullish), AND Day2's body is fully
  contained within Day1's body range (max(Day2 open,close) <= Day1 open,
  min(Day2 open,close) >= Day1 close), AND Day2's body size <=
  harami_body_ratio (default 0.60, per source) x Day1's body size.
- Entry: on the close of Day 2 itself (the pattern's own close IS the
  trigger, consistent with every other single/2-candle pattern strategy in
  this repo's shift(1) execution-lag convention -- no extra confirmation
  candle, distinct from the already-tested/rejected Piercing Line variant
  which required one and turned out too rare).
- Exit: close falls below Day1's low (per LiteFinance's stated stop-loss
  rule), OR a max_hold_days time-stop.

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
    harami_body_ratio: float = 0.60,
    trend_window: int = 50,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    low = df["low"]
    open_ = df["open"]
    close = df["close"]
    n = len(close)

    sma = close.rolling(trend_window).mean()
    downtrend = close < sma

    day1_bearish = (close < open_) & downtrend.fillna(False)
    day1_body = (open_ - close).where(day1_bearish)  # positive body size for bearish day1

    prev_day1_bearish = day1_bearish.shift(1).fillna(False)
    prev_open = open_.shift(1)
    prev_close = close.shift(1)
    prev_body = day1_body.shift(1)
    prev_low = low.shift(1)

    day2_bullish = close > open_
    day2_body = close - open_
    contained = (
        (pd.concat([open_, close], axis=1).max(axis=1) <= prev_open)
        & (pd.concat([open_, close], axis=1).min(axis=1) >= prev_close)
    )
    small_body = day2_body <= harami_body_ratio * prev_body

    is_harami = prev_day1_bearish & day2_bullish & contained.fillna(False) & small_body.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_low = np.nan

    for i in range(n):
        if in_position:
            held = i - entry_idx
            stop_hit = (not np.isnan(stop_low)) and (close.iloc[i] < stop_low)
            if stop_hit or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                stop_low = np.nan
                continue
            position.iloc[i] = 1
        else:
            if bool(is_harami.iloc[i]):
                in_position = True
                entry_idx = i
                stop_low = prev_low.iloc[i]
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
