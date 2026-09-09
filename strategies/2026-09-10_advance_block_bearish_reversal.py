"""Strategy: Advance Block bearish reversal short entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-008):
Per QuantifiedStrategies.com's Advance Block explainer
(https://www.quantifiedstrategies.com/advance-block-candlestick-pattern/,
source claims ~65% win rate in its own S&P 500 backtest): the Advance
Block is a three-candle bearish reversal pattern that appears at the end
of an uptrend, superficially resembling (but the opposite signal from)
Three White Soldiers. Source's explicit rule: "All three candlesticks
must be bullish. The second and third candlesticks must open below the
closing price of the previous candles. Expect the last two candlesticks
to have increasingly longer [upper] shadows" -- each successive bullish
candle opens weaker (a gap-down-from-prior-close open) and shows a
progressively longer upper wick (rejection at highs), signaling fading
buying conviction even while price nominally still closes up each day.

This is the mirror-opposite construction of the already-tested Three
White Soldiers strategies in this repo (which require STRONG consecutive
bullish candles with minimal upper shadows, i.e. the opposite shadow
signature) -- distinct because Advance Block specifically requires the
WEAKENING pattern (shrinking bodies / growing upper shadows / gap-down
opens) that Three White Soldiers explicitly excludes.

Signal logic
------------
- Three consecutive bullish candles (close > open) with candle2's open <
  candle1's close, AND candle3's open < candle2's close (source's
  "opens below previous closes" rule).
- Increasingly longer upper shadows: candle2's upper shadow (high-close)
  as a fraction of its own range >= candle1's, AND candle3's upper-shadow
  fraction >= candle2's (source's "increasingly longer shadows" rule).
- Uptrend precondition: close (at candle1) > SMA(trend_window) (source:
  "appears at the end of a bullish trend").
- Short entry: on the close of candle3 (the pattern completes).
- Exit: close crosses back above candle3's high (failed reversal, pattern
  invalidated), OR a fixed stop at stop_atr_mult*ATR above candle3's high,
  OR a max_hold_days time-stop.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({-1,0} short/flat)
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
    atr_window: int = 14,
    stop_atr_mult: float = 1.5,
    max_hold_days: int = 8,
) -> pd.Series:
    """Return a {-1,0} short/flat position series."""
    df = _prep(price_df)
    open_ = df["open"] if "open" in df.columns else df["close"].shift(1)
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]
    n = len(close)

    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    bullish = close > open_
    candle_range = (high - low).replace(0, np.nan)
    upper_shadow_frac = (high - close) / candle_range

    c1_bullish = bullish.shift(2)
    c2_bullish = bullish.shift(1)
    c3_bullish = bullish

    c2_opens_below_c1_close = open_.shift(1) < close.shift(2)
    c3_opens_below_c2_close = open_ < close.shift(1)

    shadow1 = upper_shadow_frac.shift(2)
    shadow2 = upper_shadow_frac.shift(1)
    shadow3 = upper_shadow_frac
    increasing_shadows = (shadow2 >= shadow1) & (shadow3 >= shadow2)

    uptrend_precondition = uptrend.shift(2).fillna(False)

    pattern_bar = (
        c1_bullish.fillna(False)
        & c2_bullish.fillna(False)
        & c3_bullish.fillna(False)
        & c2_opens_below_c1_close.fillna(False)
        & c3_opens_below_c2_close.fillna(False)
        & increasing_shadows.fillna(False)
        & uptrend_precondition
    ).fillna(False)

    atr = _atr(df, atr_window)

    c = close.to_numpy(dtype=float)
    h = high.to_numpy(dtype=float)
    pattern_arr = pattern_bar.to_numpy(dtype=bool)
    atr_arr = atr.to_numpy(dtype=float)

    position = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = 0.0
    pattern_high = 0.0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            px = c[i]
            hit_stop = px >= stop_price
            hit_reversal = px > pattern_high
            hit_time = held >= max_hold_days
            if hit_stop or hit_reversal or hit_time:
                in_position = False
                position[i] = 0
                continue
            position[i] = -1
        else:
            # Entry on the pattern-completion bar itself (candle3's close).
            if pattern_arr[i]:
                in_position = True
                entry_idx = i
                pattern_high = h[i]
                atr_at_pattern = atr_arr[i] if not np.isnan(atr_arr[i]) else 0.0
                stop_price = pattern_high + stop_atr_mult * atr_at_pattern
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
