"""Strategy: Bearish Stick Sandwich candlestick reversal (short entry).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-235):
Per QuantifiedStrategies.com's "Bearish Stick Sandwich: Candlestick
Pattern" (https://www.quantifiedstrategies.com/bearish-stick-sandwich-candlestick-pattern/,
read via browser_exec fallback -- web_extract's ddgs backend cannot
extract page content), the Bearish Stick Sandwich is the mirror-image of
the already-rejected Bullish Stick Sandwich (2026-09-09-036, this repo's
`strategies/2026-09-09_bullish_stick_sandwich.py`): a 3-candle pattern
occurring at the TOP of an uptrend:
  1. Candle 1: bullish, closing near its high.
  2. Candle 2: bearish, gapping DOWN from candle 1's close.
  3. Candle 3: bullish, engulfing candle 2's range and closing AT THE SAME
     LEVEL as candle 1's close (the "matching closes" resistance test --
     the "bread" of the sandwich).
Source's disclosed stop-loss: just below the low of the pattern (candle
2's low). Source's disclosed confirmation: a lower close on the period
following the pattern.

This is the mirror-image application of this repo's existing Bullish
Stick Sandwich implementation logic (same matching-close/gap/engulf
structure, opposite direction and opposite trend-context filter), applied
to a genuinely novel keyword (0 prior "bearish stick sandwich" hits) even
though the sibling bullish pattern was already tested and rejected in this
repo -- source material and up/down direction differ meaningfully (the
bullish version failed specifically on a repeated-support-test structure
in a downtrend; this tests a repeated-resistance-test structure in an
uptrend, a distinct market regime).

Operationalization:
  - Candle 1 (t-2): bullish (close > open), real body >= min_body_pct of
    open, AND close > SMA(trend_window) (established uptrend context,
    mirroring the sibling's downtrend filter).
  - Candle 2 (t-1): gaps down below candle 1's close (open[t-1] <
    close[t-2]) -- the "gap down from the previous close."
  - Candle 3 (t): bullish (close > open), closes within
    close_tolerance_pct of candle 1's close (the matching-close
    resistance test), AND candle 3's high tests candle 1's high (high[t]
    >= high[t-2] * (1 - high_tolerance_pct), confirming it tested the same
    resistance zone, not a random close match).
  - Entry (short): NEXT bar's close crosses below candle 3's low (one-bar
    confirmation the resistance held and sellers regained control,
    mirroring the sibling's confirmation logic).
  - Exit: close crosses back above candle 1's high (failed resistance,
    invalidate the pattern), a max_hold_days time-stop, or a target of
    reward_atr_mult*ATR below the entry price.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (position: -1 short/0 flat)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
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
    high_tolerance_pct: float = 0.01,
    atr_window: int = 14,
    reward_atr_mult: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {-1, 0} short/flat position series."""
    df = _prep(price_df)
    open_ = df["open"] if "open" in df.columns else df["close"].shift(1)
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]
    n = len(close)

    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    c1_open = open_.shift(2)
    c1_close = close.shift(2)
    c1_high = high.shift(2)
    c1_bullish = c1_close > c1_open
    c1_body_pct = (c1_close - c1_open).abs() / c1_open.replace(0, np.nan)
    c1_uptrend_ctx = uptrend.shift(2).fillna(False)

    c2_open = open_.shift(1)
    c2_gap_below_c1_close = c2_open < c1_close

    c3_open = open_
    c3_close = close
    c3_low = low
    c3_high = high
    c3_bullish = c3_close > c3_open
    c3_close_near_c1 = (c3_close - c1_close).abs() <= (c1_close.abs() * close_tolerance_pct)
    c3_high_tests_c1_high = c3_high >= (c1_high * (1 - high_tolerance_pct))

    pattern_bar = (
        c1_bullish
        & (c1_body_pct >= min_body_pct).fillna(False)
        & c1_uptrend_ctx
        & c2_gap_below_c1_close.fillna(False)
        & c3_bullish
        & c3_close_near_c1.fillna(False)
        & c3_high_tests_c1_high.fillna(False)
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
    pattern_high = 0.0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            px = c[i]
            hit_target = px <= target_price
            hit_stop = px > pattern_high
            hit_time = held >= max_hold_days
            if hit_target or hit_stop or hit_time:
                in_position = False
                position[i] = 0
                continue
            position[i] = -1
        else:
            # Confirmation: this bar's close breaks below the pattern's
            # candle-3 low (one bar after the pattern bar itself).
            if i >= 1 and pattern_arr[i - 1] and c[i] < l[i - 1]:
                in_position = True
                entry_idx = i
                pattern_high = h[i - 1]
                atr_at_pattern = atr_arr[i - 1] if not np.isnan(atr_arr[i - 1]) else 0.0
                target_price = c[i] - reward_atr_mult * atr_at_pattern
                position[i] = -1
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
