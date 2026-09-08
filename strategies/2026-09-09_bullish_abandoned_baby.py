"""Strategy: Bullish Abandoned Baby candlestick reversal (long entry).

Hypothesis (this iteration):
Per https://therobusttrader.com/bullish-abandoned-baby/ and
https://trading-charts.com/patterns/bullish/bullish-abandoned-baby, the
Bullish Abandoned Baby is a 3-candle reversal pattern distinct from the
already-tested Morning Star family in this repo: candle 1 is bearish
(part of an ongoing downtrend, close < SMA(trend_window)); candle 2 is a
doji (very small real body relative to its range) that GAPS DOWN from
candle 1 (candle2.high < candle1.low); candle 3 GAPS UP from candle 2
(candle3.low > candle2.high) and closes as a tall bullish candle. Per the
source's own explicit differentiator from Morning Star: "It's important
that the real bodies of the three candlesticks don't overlap from bar 1
to 2 and from bar 2 to 3" -- i.e. two genuine price gaps with no body
overlap, a strictly stronger (and rarer) condition than Morning Star's
midpoint-recovery rule (already tested in this repo). Long entry on
candle 3's own close (pattern is fully formed and confirmed by the third
candle's gap-up + strong close, no extra confirmation bar needed per
source); exit on a mean-reversion target (close crossing back above a
short SMA), a hard stop below candle 2's low (pattern invalidated), or a
max_hold_days time-stop.

Distinct from every prior candlestick pattern tested in this repo
(Morning Star, Bullish Engulfing, Bullish Harami, Piercing Line, Bullish
Kicker, Dark Cloud Cover, Stick Sandwich, Three Outside Up, Mat Hold,
Belt Hold, Three Line Strike [feasibility-rejected, too rare]) by
requiring TWO genuine non-overlapping gaps (down then up) around a doji,
rather than a single gap, an engulf, or a midpoint-recovery condition.

Signal logic
------------
- candle1 (i-2): bearish (close < open), close < SMA(trend_window)
  (downtrend context).
- candle2 (i-1): doji -- |close-open| <= doji_body_pct * (high-low), AND
  gaps down from candle1: candle2.high < candle1.low * (1 - gap_pct).
- candle3 (i): gaps up from candle2: candle3.low > candle2.high *
  (1 + gap_pct), AND bullish (close > open) with real body >=
  min_body_pct of open (a "tall" bullish candle per source).
- Entry (long): candle3's own close (pattern fully confirmed intrabar).
- Exit: close crosses above SMA(exit_sma_window) (mean-reversion target
  reached), OR close drops below candle2's low (pattern failed), OR a
  max_hold_days time-stop.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

Sources:
    https://therobusttrader.com/bullish-abandoned-baby/
    https://trading-charts.com/patterns/bullish/bullish-abandoned-baby
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
    doji_body_pct: float = 0.1,
    gap_pct: float = 0.001,
    min_body_pct: float = 0.01,
    exit_sma_window: int = 10,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    open_ = df["open"] if "open" in df.columns else df["close"].shift(1)
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]
    n = len(close)

    sma_trend = close.rolling(trend_window).mean()
    sma_exit = close.rolling(exit_sma_window).mean()
    downtrend = close < sma_trend

    c1_open = open_.shift(2)
    c1_close = close.shift(2)
    c1_low = low.shift(2)
    c1_bearish = c1_close < c1_open
    c1_downtrend_ctx = downtrend.shift(2).fillna(False)

    c2_open = open_.shift(1)
    c2_close = close.shift(1)
    c2_high = high.shift(1)
    c2_low = low.shift(1)
    c2_range = (high.shift(1) - low.shift(1)).replace(0, np.nan)
    c2_doji = ((c2_close - c2_open).abs() / c2_range) <= doji_body_pct
    c2_gap_down = c2_high < (c1_low * (1 - gap_pct))

    c3_open = open_
    c3_close = close
    c3_low = low
    c3_bullish = c3_close > c3_open
    c3_body_pct = (c3_close - c3_open) / c3_open.replace(0, np.nan)
    c3_gap_up = c3_low > (c2_high * (1 + gap_pct))

    pattern_bar = (
        c1_bearish
        & c1_downtrend_ctx
        & c2_doji.fillna(False)
        & c2_gap_down.fillna(False)
        & c3_bullish
        & (c3_body_pct >= min_body_pct).fillna(False)
        & c3_gap_up.fillna(False)
    ).fillna(False)

    c = close.to_numpy(dtype=float)
    sma_exit_arr = sma_exit.to_numpy(dtype=float)
    c2_low_arr = c2_low.to_numpy(dtype=float)
    pattern_arr = pattern_bar.to_numpy(dtype=bool)

    position = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = 0.0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            px = c[i]
            hit_target = (not np.isnan(sma_exit_arr[i])) and px >= sma_exit_arr[i]
            hit_stop = px < stop_price
            hit_time = held >= max_hold_days
            if hit_target or hit_stop or hit_time:
                in_position = False
                position[i] = 0
                continue
            position[i] = 1
        else:
            if pattern_arr[i]:
                in_position = True
                entry_idx = i
                stop_price = c2_low_arr[i] if not np.isnan(c2_low_arr[i]) else 0.0
                position[i] = 1
            else:
                position[i] = 0

    return pd.Series(position, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
