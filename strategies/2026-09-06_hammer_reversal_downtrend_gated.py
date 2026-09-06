"""Strategy: Hammer candlestick bullish reversal, downtrend-gated, long-only.

Hypothesis (see knowledge_base id 2026-09-06-147):
Per TradingView's "Candlestick Patterns" script description
(https://www.tradingview.com/scripts/hammer/) and the Google-search-surfaced
strategy snippet ("The strategy goes long on the next bar open when a hammer
is detected, with a stop loss at the low of the hammer bar and a target at
the high"): a Hammer is a single-candle bullish reversal pattern with a
small body near the top of its range and a lower wick at least
wick_to_body_ratio (default 2.0x, per source) times the body size, appearing
after a downtrend. First Hammer-pattern strategy in this repo (distinct from
Bullish Engulfing 2026-09-04-102, Three White Soldiers 2026-09-06-132, and
Marubozu 2026-09-06-146, all of which use different candle-anatomy criteria
-- Hammer's defining feature is the disproportionate lower wick, not body
dominance or multi-candle relative position).

Signal logic
------------
- Candle anatomy: body = |close-open|; lower_wick = min(open,close)-low;
  upper_wick = high-max(open,close); full_range = high-low.
- Hammer bar: lower_wick >= wick_to_body_ratio * body (small body, long
  lower wick), AND upper_wick <= body (minimal upper wick, per standard
  Hammer definition), AND the bar occurs after a downtrend (close <
  SMA(trend_window), the standard "appears after a downtrend" precondition
  from every source consulted).
- Entry: per the TradingView-snippet's own stated rule, "goes long on the
  next bar['s] open when a hammer is detected" -- approximated at daily-bar
  granularity as entering at the NEXT bar's close (this repo's returns
  model is close-to-close, so "next bar open" is approximated by acting on
  the signal one bar after detection, consistent with every other strategy
  in this repo's shift(1) execution-lag convention).
- Exit: per source, "stop loss at the low of the hammer bar and a target at
  the high" -- operationalized as exit when close falls below the hammer
  bar's low (stop) OR close rises above hammer_target_mult * the hammer
  bar's high-low range added to the hammer's high (target), OR a
  max_hold_days time-stop backstop.

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
    wick_to_body_ratio: float = 2.0,
    trend_window: int = 50,
    hammer_target_mult: float = 1.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    open_ = df["open"]
    close = df["close"]
    n = len(close)

    body = (close - open_).abs()
    lower_wick = pd.concat([open_, close], axis=1).min(axis=1) - low
    upper_wick = high - pd.concat([open_, close], axis=1).max(axis=1)
    body_safe = body.replace(0.0, np.nan)

    sma = close.rolling(trend_window).mean()
    downtrend = close < sma

    is_hammer = (
        (lower_wick >= wick_to_body_ratio * body_safe.fillna(0.0))
        & (upper_wick <= body_safe.fillna(np.inf))
        & downtrend.fillna(False)
        & (body > 0)
    )

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_low = np.nan
    target_high = np.nan
    pending_bar = None  # index of a detected hammer bar, entered next bar

    for i in range(n):
        if in_position:
            held = i - entry_idx
            stop_hit = (not np.isnan(stop_low)) and (close.iloc[i] < stop_low)
            target_hit = (not np.isnan(target_high)) and (close.iloc[i] > target_high)
            if stop_hit or target_hit or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                stop_low = np.nan
                target_high = np.nan
                continue
            position.iloc[i] = 1
        else:
            if pending_bar is not None and pending_bar == i - 1:
                in_position = True
                entry_idx = i
                stop_low = low.iloc[pending_bar]
                hammer_range = high.iloc[pending_bar] - low.iloc[pending_bar]
                target_high = high.iloc[pending_bar] + hammer_target_mult * hammer_range
                position.iloc[i] = 1
                pending_bar = None
                continue
            pending_bar = i if bool(is_hammer.iloc[i]) else None
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
