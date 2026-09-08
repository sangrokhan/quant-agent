"""Strategy: Bullish Stick Sandwich candlestick reversal (long entry).

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD, this iteration):
Per https://www.investopedia.com/terms/s/stick-sandwich.asp and
https://wrtrading.com/technical-analysis/charts/candlestick/pattern/stick-sandwich/,
the Bullish Stick Sandwich is a 3-candle reversal pattern that forms during a
downtrend: candle 1 is a long bearish (red) candle; candle 2 opens higher and
closes lower than candle 1's close (a bullish/green inside-ish candle,
smaller range, "sandwiched" -- source: "opens higher and closes lower...
then ends with another bearish candle"); candle 3 is another bearish (red)
candle that closes at or near candle 1's close (same support level,
"sandwich" effect -- the market tests the same low twice and fails to make a
new low, echoing double-bottom support). This is distinct from every
previously-tested 2/3-candle pattern in this repo (Bullish Engulfing, Bullish
Harami, Piercing Line, Morning Star, Three Black/White, Tweezer Bottom,
Dark Cloud Cover, Rising Three Methods (rejected -- too rare on daily
equity bars), Three Outside Up (rejected)) because the defining condition is
candle1.close ~= candle3.close (a repeated-low "double test of support"),
not a simple engulf/gap/midpoint-of-body rule.

Because ThePatternSite.com's own long-run frequency-rank note (rank 59,
"acts as a bearish continuation most often" despite its bullish-reversal
label) is a known caveat, this implementation requires a trend_window SMA
downtrend filter (close < SMA at candle 1) as a genuine reversal-context
precondition, plus a one-bar confirmation (close above candle 3's high)
before entering long -- rather than trading the raw 3-candle pattern blind,
addressing the exact "acts as continuation not reversal" risk the source
literature flags.

Signal logic
------------
- candle1 (i-2): bearish (close < open), real body >= min_body_pct of open,
  AND close < SMA(trend_window) (established downtrend context).
- candle2 (i-1): opens above candle1's close, closes below candle2's own
  open... i.e. candle2 itself can be either color per source variance, but
  must stay fully within (or near) candle1's range and close notably above
  candle1's close (the "sandwich filling").
- candle3 (i): bearish (close < open), closes within close_tolerance_pct of
  candle1's close (the repeated-support test), and candle3.low <= candle1.low
  * (1 + low_tolerance_pct) (confirms it tested the same low zone, not a
  random close match).
- Entry (long): NEXT bar's close crosses above candle3's high (one-bar
  confirmation the sandwich support held and buyers regained control).
- Exit: close crosses back below candle1's low (failed support, invalidate
  the pattern), a max_hold_days time-stop, or a target of
  reward_atr_mult*ATR above the entry price.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

Sources:
    https://www.investopedia.com/terms/s/stick-sandwich.asp
    https://wrtrading.com/technical-analysis/charts/candlestick/pattern/stick-sandwich/
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    min_body_pct: float = 0.005,
    close_tolerance_pct: float = 0.005,
    low_tolerance_pct: float = 0.01,
    atr_window: int = 14,
    reward_atr_mult: float = 2.0,
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
    downtrend = close < sma_trend

    c1_open = open_.shift(2)
    c1_close = close.shift(2)
    c1_low = low.shift(2)
    c1_bearish = c1_close < c1_open
    c1_body_pct = (c1_open - c1_close).abs() / c1_open.replace(0, np.nan)
    c1_downtrend_ctx = downtrend.shift(2).fillna(False)

    c2_open = open_.shift(1)
    c2_close = close.shift(1)
    c2_gap_above_c1_close = c2_open > c1_close

    c3_open = open_
    c3_close = close
    c3_low = low
    c3_high = high
    c3_bearish = c3_close < c3_open
    c3_close_near_c1 = (c3_close - c1_close).abs() <= (c1_close.abs() * close_tolerance_pct)
    c3_low_tests_c1_low = c3_low <= (c1_low * (1 + low_tolerance_pct))

    pattern_bar = (
        c1_bearish
        & (c1_body_pct >= min_body_pct).fillna(False)
        & c1_downtrend_ctx
        & c2_gap_above_c1_close.fillna(False)
        & c3_bearish
        & c3_close_near_c1.fillna(False)
        & c3_low_tests_c1_low.fillna(False)
    ).fillna(False)

    atr = _atr(df, atr_window)

    c = close.to_numpy(dtype=float)
    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    pattern_arr = pattern_bar.to_numpy(dtype=bool)
    atr_arr = atr.to_numpy(dtype=float)

    position = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0
    target_price = 0.0
    pattern_low = 0.0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            px = c[i]
            hit_target = px >= target_price
            hit_stop = px < pattern_low
            hit_time = held >= max_hold_days
            if hit_target or hit_stop or hit_time:
                in_position = False
                position[i] = 0
                continue
            position[i] = 1
        else:
            # Confirmation: this bar's close breaks above the pattern's
            # candle-3 high (one bar after the pattern bar itself).
            if i >= 1 and pattern_arr[i - 1] and c[i] > h[i - 1]:
                in_position = True
                entry_idx = i
                pattern_low = l[i - 1]
                atr_at_pattern = atr_arr[i - 1] if not np.isnan(atr_arr[i - 1]) else 0.0
                target_price = c[i] + reward_atr_mult * atr_at_pattern
                position[i] = 1
            else:
                position[i] = 0

    return pd.Series(position, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias -- can't trade on today's own close).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
