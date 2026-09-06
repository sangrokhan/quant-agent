"""Strategy: Tweezer Bottom breakout-confirmed reversal, downtrend-gated,
long-only.

Hypothesis (see knowledge_base id 2026-09-06-152):
Per MNCL Group's Tweezer Bottom guide
(https://www.mnclgroup.com/tweezer-bottom-candlestick-pattern-guide): "A
Tweezer Bottom is a two-candle bullish reversal pattern that forms after a
downtrend when two consecutive candles establish nearly identical lows...
repeated rejection of lower prices may indicate downside momentum is
weakening." The source's own recommended "Breakout Confirmation Strategy":
"Identify a valid Tweezer Bottom. Wait for price to move above pattern
resistance [the 2-candle pattern's high]." First Tweezer-family pattern in
this repo -- distinct from Hammer (2026-09-06-147, single candle), Piercing
Line (2026-09-06-148, midpoint-cross), Bullish Harami (2026-09-06-150,
contained-body), and Bullish Engulfing (2026-09-04-102, full-body
overtake): Tweezer Bottom is defined purely by matching LOWS across two
candles, independent of body size/overlap relationships.

Signal logic
------------
- Downtrend gate: close < SMA(trend_window) on the pattern's 2nd day.
- Tweezer detection: two consecutive days (Day1, Day2) whose lows are
  within tweezer_tolerance_pct of each other (default 0.3%, i.e. "nearly
  identical lows" per source).
- Entry trigger (source's own "Breakout Confirmation" rule): within
  breakout_expiry_bars of the pattern's Day2, a subsequent close breaks
  above the pattern's high (max(Day1 high, Day2 high)) -> long entry on
  that breakout bar's close.
- Exit: close falls back below the pattern's low (failure), or a
  max_hold_days time-stop.

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
    tweezer_tolerance_pct: float = 0.003,
    trend_window: int = 50,
    breakout_expiry_bars: int = 5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]
    n = len(close)

    sma = close.rolling(trend_window).mean()
    downtrend = (close < sma).fillna(False)

    prev_low = low.shift(1)
    prev_high = high.shift(1)

    lows_match = (abs(low - prev_low) / prev_low) <= tweezer_tolerance_pct
    is_tweezer = lows_match.fillna(False) & downtrend

    pattern_high = pd.concat([high, prev_high], axis=1).max(axis=1)
    pattern_low = pd.concat([low, prev_low], axis=1).min(axis=1)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_low = np.nan

    # Track pending tweezer patterns awaiting breakout confirmation.
    pending_high = np.nan
    pending_low = np.nan
    pending_since = -1

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
            continue

        # Not in position: check for a new tweezer pattern forming today.
        if bool(is_tweezer.iloc[i]):
            pending_high = pattern_high.iloc[i]
            pending_low = pattern_low.iloc[i]
            pending_since = i

        # Check whether a pending pattern's breakout confirms today.
        if pending_since >= 0 and (i - pending_since) <= breakout_expiry_bars:
            if not np.isnan(pending_high) and close.iloc[i] > pending_high:
                in_position = True
                entry_idx = i
                stop_low = pending_low
                position.iloc[i] = 1
                pending_since = -1
                continue
        elif pending_since >= 0 and (i - pending_since) > breakout_expiry_bars:
            pending_since = -1  # expired, unconfirmed

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
