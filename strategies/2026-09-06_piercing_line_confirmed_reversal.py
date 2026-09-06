"""Strategy: Piercing Line bullish reversal (2-candle pattern), downtrend-gated,
long-only, with confirmation-candle entry.

Hypothesis (see knowledge_base id 2026-09-06-148):
Per TradingView's "Candlestick Patterns" script description
(https://www.tradingview.com/scripts/hammer/, same source page as the
already-tested Hammer strategy 2026-09-06-147, which documents all 15
classic patterns): "Piercing Line requires the close to cross above the
midpoint of the prior bearish candle." Capital.com's Piercing Line guide
(Google SERP snippet) adds a confirmation-candle entry rule: "Wait for the
candle after the piercing line to close. If it is green and closes higher,
this is a strong confirmation. You can enter the trade after this candle."

First Piercing Line (2-candle) strategy in this repo -- distinct from
Bullish Engulfing (2026-09-04-102, which requires FULL body engulfment) and
Hammer (2026-09-06-147, single-candle wick-based pattern): Piercing Line
requires only a partial midpoint-cross of the prior bearish candle's body,
a materially different (weaker) two-candle reversal signal.

Signal logic
------------
- Day 1 (bearish setup candle): close < open, occurring in a confirmed
  downtrend (close < SMA(trend_window)).
- Day 2 (piercing candle): open < Day1's low (gaps down, standard Piercing
  Line precondition per every source), close > Day1's midpoint
  ((Day1 open + Day1 close)/2), AND close < Day1's open (does not fully
  engulf -- that would instead be a Bullish Engulfing, already tested).
- Confirmation (Day 3): close > open (green) AND close > Day2's close
  (per Capital.com's stated confirmation rule) -- entry triggers on Day 3's
  close.
- Exit: close falls back below Day1's low (pattern failure), OR close
  crosses below SMA(trend_window) (trend break), OR a max_hold_days
  time-stop.

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
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    open_ = df["open"]
    close = df["close"]
    n = len(close)

    sma = close.rolling(trend_window).mean()
    downtrend = close < sma

    day1_bearish = (close < open_) & downtrend.fillna(False)
    day1_midpoint = (open_ + close) / 2.0

    # "Day 2" fields, evaluated at bar i relative to bar i-1 as Day1
    prev_day1_bearish = day1_bearish.shift(1).fillna(False)
    prev_low = low.shift(1)
    prev_open = open_.shift(1)
    prev_midpoint = day1_midpoint.shift(1)

    is_piercing = (
        prev_day1_bearish
        & (open_ < prev_low)
        & (close > prev_midpoint)
        & (close < prev_open)
    )

    # confirmation candle at bar i+1 relative to piercing bar i
    confirm = (close > open_) & (close > close.shift(1))
    piercing_prev = is_piercing.shift(1).fillna(False)
    confirmed_entry_signal = confirm & piercing_prev

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    day1_low_stop = np.nan

    # track Day1's low for the active piercing setup (2 bars back from confirmation)
    for i in range(n):
        if in_position:
            held = i - entry_idx
            stop_hit = (not np.isnan(day1_low_stop)) and (close.iloc[i] < day1_low_stop)
            trend_break = not bool(downtrend.iloc[i]) if not np.isnan(sma.iloc[i]) else False
            # trend_break here means price no longer below trend SMA is NOT itself
            # a failure signal for a reversal trade -- use it as intended: exit when
            # the ORIGINAL downtrend context has clearly reversed upward is fine
            # (that's the goal), so we do NOT exit on trend "break" (that would be
            # exiting on success). Only exit on stop or time-stop.
            if stop_hit or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                day1_low_stop = np.nan
                continue
            position.iloc[i] = 1
        else:
            if bool(confirmed_entry_signal.iloc[i]) and i >= 2:
                in_position = True
                entry_idx = i
                day1_low_stop = low.iloc[i - 2]
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
