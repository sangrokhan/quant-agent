"""Strategy: Dark Cloud Cover bearish reversal short entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-062):
The Dark Cloud Cover is a two-candle bearish reversal pattern (per
https://www.protradingschool.com/dark-cloud-cover-candlestick-pattern/):
(1) a bullish candle (close > open) forming within/after an established
uptrend; (2) the next candle opens AT OR ABOVE the prior candle's close
(a gap-up open, "gives the impression bullish momentum may continue"),
then reverses sharply and closes BELOW the MIDPOINT of the first candle's
real body -- "the strongest bearish reaction is what gives the pattern
its reversal potential". The source explicitly stresses the pattern
"should never be traded blindly without confirmation" and recommends
combining it with trend analysis / higher-timeframe structure -- so this
implementation requires the pattern to occur while price is above a
longer-term SMA(trend_window) (an established uptrend, the pattern's own
stated precondition) and adds a one-bar-later confirmation (next close
below the pattern bar's low) before entering short.

This is the first Dark Cloud Cover (bearish two-candle reversal, gap-up
open + midpoint-of-first-body close) construction in this repo -- distinct
from the already-tested bullish mirror-family patterns (Bullish Engulfing
2026-09-06/2026-09-08, Piercing Line 2026-09-06, Morning Star 2026-09-06,
Three White Soldiers 2026-09-06) which are all upside reversal/continuation
setups, and from the two single-candle bearish patterns already tested
(Hammer-in-downtrend is bullish; none of Three Black Crows [2026-09-07,
three consecutive bearish closes, no gap] or Wyckoff Upthrust [false
breakout above range resistance, no candle-body-midpoint condition] use
this pattern's specific gap-up-then-close-past-midpoint definition).

Short entry: pattern confirmed (bullish candle -> gap-up-open bearish
candle closing below the first candle's body midpoint) while close >
SMA(trend_window) is FALSE is excluded (source requires the pattern to
appear "during an uptrend"); confirmation bar closes below the pattern
bar's low. Exit: close crosses back above the pattern bar's high (failed
reversal), a max_hold_days time-stop, or a fixed stop at
stop_atr_mult*ATR above the pattern bar's high.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({-1,0} short/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

Source: https://www.protradingschool.com/dark-cloud-cover-candlestick-pattern/
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
    atr_window: int = 14,
    stop_atr_mult: float = 1.5,
    max_hold_days: int = 10,
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

    prev_open = open_.shift(1)
    prev_close = close.shift(1)
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_bullish = prev_close > prev_open
    prev_body_pct = (prev_close - prev_open).abs() / prev_open.replace(0, np.nan)
    prev_body_mid = (prev_open + prev_close) / 2.0

    # Today gaps up (open >= prior close) then reverses to close below the
    # prior candle's body midpoint -- the Dark Cloud Cover trigger bar.
    gap_up_open = open_ >= prev_close
    close_below_mid = close < prev_body_mid
    is_bearish_today = close < open_

    pattern_bar = (
        prev_bullish
        & (prev_body_pct >= min_body_pct).fillna(False)
        & gap_up_open
        & close_below_mid
        & is_bearish_today
        & uptrend.shift(1).fillna(False)
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
    stop_price = 0.0
    pattern_low = 0.0
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
            # Confirmation: this bar must be AFTER a pattern bar and close
            # below the pattern bar's low (continuation confirmation).
            if i >= 1 and pattern_arr[i - 1] and c[i] < l[i - 1]:
                in_position = True
                entry_idx = i
                pattern_low = l[i - 1]
                pattern_high = h[i - 1]
                atr_at_pattern = atr_arr[i - 1] if not np.isnan(atr_arr[i - 1]) else 0.0
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
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias -- can't trade on today's own close).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
