"""Strategy: Bullish Kicker gap-reversal, downtrend-gated, long-only.

Hypothesis (see knowledge_base id 2026-09-06-155):
Per QuantifiedStrategies.com's Bullish Kicker guide
(https://www.quantifiedstrategies.com/bullish-kicker-candlestick-pattern/):
"The pattern starts with a bearish candle... The second candle gaps to the
upside, and opens above the previous day's close [we use the stricter
'above previous day's OPEN' variant the source also describes for a 'kick'
gap, distinct from a plain gap-up-over-close]. It continues straight up and
ends as a bullish candlestick. The gap should not be filled by the wick of
the second candlestick, but be left untouched. In other words, the
candlestick has a tiny or nonexistent lower wick." Occurring after a
downtrend, per the source, makes it "a sort of reversal pattern" (as
opposed to continuation after an uptrend, out of scope here to keep this
iteration's hypothesis tight). First Bullish Kicker strategy in this repo
-- distinct from Bullish Engulfing (2026-09-04-102, no gap requirement) and
Gap-and-Go (2026-09-06-153, requires only close>open follow-through on a
plain gap-up, no bearish setup candle or specific "gap above prior OPEN,
untouched lower wick" strength criteria).

Signal logic
------------
- Downtrend gate: close < SMA(trend_window) on Day1.
- Day1 (bearish setup candle): close < open, in the confirmed downtrend.
- Day2 (kicker candle): open > Day1's own open (the "kick" -- gaps above
  the ENTIRE prior candle, not just its close) AND close > open (bullish)
  AND minimal lower wick (low >= open - max_wick_pct * (close - open), per
  source's "tiny or nonexistent lower wick, gap left untouched").
- Entry: on Day2's close (shift(1) execution-lag convention, consistent
  with every pattern strategy in this repo).
- Exit: close falls back below Day2's own low (failure of the pattern,
  i.e. the gap gets filled after all) OR a max_hold_days time-stop.

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
    max_wick_pct: float = 0.15,
    trend_window: int = 50,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    open_ = df["open"]
    low = df["low"]
    close = df["close"]
    n = len(close)

    sma = close.rolling(trend_window).mean()
    downtrend = (close < sma).fillna(False)

    day1_bearish = (close < open_) & downtrend
    prev_open = open_.shift(1)
    prev_day1_bearish = day1_bearish.shift(1).fillna(False)

    day2_bullish = close > open_
    day2_body = (close - open_).clip(lower=1e-9)
    gapped_above_prev_open = open_ > prev_open
    small_lower_wick = (open_ - low) <= (max_wick_pct * day2_body)

    is_kicker = prev_day1_bearish & day2_bullish & gapped_above_prev_open & small_lower_wick.fillna(False)

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
            if bool(is_kicker.iloc[i]):
                in_position = True
                entry_idx = i
                stop_low = low.iloc[i]
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
