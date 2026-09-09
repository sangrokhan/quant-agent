"""Strategy: Bullish Counterattack Lines reversal, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-009):
Per TheTradingAnalyst's Counterattack Lines guide
(https://thetradinganalyst.com/counterattack-lines-pattern/): the Bullish
Counterattack Lines pattern appears during a downtrend and consists of
two candles: candle1 is a large bearish candle (continuing the
downtrend); candle2 opens LOWER than candle1's close (often gapping
down, extending the bearish move initially) but then rallies sharply to
close NEAR candle1's close -- "the two candles finish with prices that
are close to each other... regardless of where they started," signaling
buyers have forcefully absorbed the continued selling and fought the
close back to parity. The source explicitly distinguishes this from the
Engulfing pattern: Counterattack requires matching CLOSES (a "stalemate"
at the same level), not one candle's body engulfing the other's.

First Counterattack Lines strategy in this repo -- distinct from all
prior two-candle reversal patterns tested (Bullish Engulfing requires
candle2's body to fully engulf candle1's; Piercing Line requires candle2
to close above candle1's midpoint but below its open; Dark Cloud Cover is
the bearish mirror using a midpoint-of-body threshold, not a matched-
close threshold) since none of those use a "closes converge to
approximately the same level" condition.

Signal logic
------------
- Downtrend precondition: close (at candle1) < SMA(trend_window) (source:
  "should appear during an obvious existing trend" -- specifically a
  downtrend for the bullish variant).
- candle1 (prior bar) is bearish (close < open) with a real body >=
  min_body_pct of its own open (source: "usually having a big body").
- candle2 (today) opens below candle1's close (gap-down or lower open,
  source: "starts lower... sometimes with a gap down").
- candle2's close is within `close_match_tolerance` (as a fraction of
  candle1's own trading range) of candle1's close (the "counterattack"
  matched-close condition).
- candle2 must itself close higher than it opened (close > open --
  confirms the rally-back-to-parity actually happened intraday, not just
  a coincidental close level).
- Entry: long on candle2's close (pattern completion).
- Exit: close falls back below candle2's low (failed reversal), OR after
  `max_hold_days` (avoid indefinite holds).

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
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
    min_body_pct: float = 0.005,
    close_match_tolerance: float = 0.15,
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

    prev_open = open_.shift(1)
    prev_close = close.shift(1)
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_range = (prev_high - prev_low).replace(0, np.nan)

    prev_bearish = prev_close < prev_open
    prev_body_pct = (prev_open - prev_close).abs() / prev_open.replace(0, np.nan)

    today_opens_lower = open_ < prev_close
    today_bullish = close > open_
    close_match = (close - prev_close).abs() <= close_match_tolerance * prev_range

    pattern_bar = (
        prev_bearish
        & (prev_body_pct >= min_body_pct).fillna(False)
        & today_opens_lower
        & today_bullish
        & close_match.fillna(False)
        & downtrend.shift(1).fillna(False)
    ).fillna(False)

    c = close.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    pattern_arr = pattern_bar.to_numpy(dtype=bool)

    position = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = 0.0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            px = c[i]
            if px < stop_price or held >= max_hold_days:
                in_position = False
                position[i] = 0
                continue
            position[i] = 1
        else:
            if pattern_arr[i]:
                in_position = True
                entry_idx = i
                stop_price = l[i]
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
