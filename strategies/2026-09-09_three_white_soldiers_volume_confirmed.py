"""Strategy: Three White Soldiers candlestick pattern, VOLUME-CONFIRMED
immediate entry (long).

Hypothesis (this iteration):
Per https://www.colibritrader.com/three-white-soldiers-candlestick-pattern/
and https://www.quantifiedstrategies.com/three-white-soldiers-candlestick-pattern/,
the classic Three White Soldiers pattern is three consecutive long-bodied
bullish candles, each opening within the prior candle's real body, each
closing near its own high (small upper wicks). Per
colibritrader.com's own explicit claim: "Volume is your truth detector in
the market. A genuine three white soldiers candlestick pattern should
always be backed by rising volume" -- i.e. each of the three candles
should show volume at or above the prior candle's volume (a monotonic
rising-volume confirmation), distinguishing a genuine institutional
takeover from a low-conviction retail bounce.

This is distinct from the already-rejected pullback-entry Three White
Soldiers variant in this repo (2026-09-06-132, decisive 0/14, which
required a subsequent pullback before entering) in TWO ways: (1) this
version REQUIRES a volume-confirmation filter (monotonically rising
volume across all 3 candles) the prior version did not test, and (2) this
version enters immediately on the close of the third (confirming) candle
rather than waiting for a pullback -- addressing the possibility that the
pullback-entry version's fixed-lookback pullback wait period simply
missed too many genuine continuations.

Signal logic
------------
- candle1 (i-2), candle2 (i-1), candle3 (i): all bullish (close > open),
  real body >= min_body_pct of open.
- Staircase overlap: candle2.open within candle1's real body
  [candle1.open, candle1.close]; candle3.open within candle2's real body.
- Small upper wicks: (high - close) / (high - low) <= max_upper_wick_pct
  for all three candles.
- Volume confirmation: volume[i-1] >= volume[i-2] * (1 - vol_tolerance)
  AND volume[i] >= volume[i-1] * (1 - vol_tolerance) (monotonically
  non-decreasing volume across all three candles, small tolerance for
  near-flat readings).
- Trend context: candle1 forms after a downtrend (close.shift(2) <
  SMA(trend_window).shift(2)), per the pattern's own reversal framing.
- Entry (long): candle3's own close (immediate entry, no pullback wait).
- Exit: close crosses below candle1's low (pattern failed/invalidated),
  a max_hold_days time-stop, or a target of reward_atr_mult*ATR above
  the entry price.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

Sources:
    https://www.colibritrader.com/three-white-soldiers-candlestick-pattern/
    https://www.quantifiedstrategies.com/three-white-soldiers-candlestick-pattern/
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
    max_upper_wick_pct: float = 0.25,
    vol_tolerance: float = 0.05,
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
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)
    n = len(close)

    sma_trend = close.rolling(trend_window).mean()
    downtrend = close < sma_trend

    def _bullish_ok(open_s, close_s, high_s, low_s):
        body_pct = (close_s - open_s) / open_s.replace(0, np.nan)
        bullish = close_s > open_s
        upper_wick_pct = (high_s - close_s) / (high_s - low_s).replace(0, np.nan)
        return (
            bullish
            & (body_pct >= min_body_pct).fillna(False)
            & (upper_wick_pct <= max_upper_wick_pct).fillna(False)
        )

    c1_open, c1_close, c1_high, c1_low, c1_vol = (
        open_.shift(2), close.shift(2), high.shift(2), low.shift(2), volume.shift(2)
    )
    c2_open, c2_close, c2_high, c2_low, c2_vol = (
        open_.shift(1), close.shift(1), high.shift(1), low.shift(1), volume.shift(1)
    )
    c3_open, c3_close, c3_high, c3_low, c3_vol = open_, close, high, low, volume

    c1_ok = _bullish_ok(c1_open, c1_close, c1_high, c1_low)
    c2_ok = _bullish_ok(c2_open, c2_close, c2_high, c2_low)
    c3_ok = _bullish_ok(c3_open, c3_close, c3_high, c3_low)

    c2_opens_within_c1 = (c2_open >= c1_open.where(c1_open < c1_close, c1_close)) & (
        c2_open <= c1_close.where(c1_close > c1_open, c1_open)
    )
    c3_opens_within_c2 = (c3_open >= c2_open.where(c2_open < c2_close, c2_close)) & (
        c3_open <= c2_close.where(c2_close > c2_open, c2_open)
    )

    vol_confirm = (
        (c2_vol >= c1_vol * (1 - vol_tolerance))
        & (c3_vol >= c2_vol * (1 - vol_tolerance))
    ).fillna(False)

    downtrend_ctx = downtrend.shift(2).fillna(False)

    pattern_bar = (
        c1_ok & c2_ok & c3_ok
        & c2_opens_within_c1.fillna(False)
        & c3_opens_within_c2.fillna(False)
        & vol_confirm
        & downtrend_ctx
    ).fillna(False)

    atr = _atr(df, atr_window)

    c = close.to_numpy(dtype=float)
    pattern_arr = pattern_bar.to_numpy(dtype=bool)
    atr_arr = atr.to_numpy(dtype=float)
    c1_low_arr = c1_low.to_numpy(dtype=float)

    position = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0
    target_price = 0.0
    stop_price = 0.0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            px = c[i]
            hit_target = px >= target_price
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
                stop_price = c1_low_arr[i] if not np.isnan(c1_low_arr[i]) else 0.0
                atr_here = atr_arr[i] if not np.isnan(atr_arr[i]) else 0.0
                target_price = c[i] + reward_atr_mult * atr_here
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
