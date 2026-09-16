"""Strategy: Tirone Levels (Midpoint Method) breakout / retracement exit,
SMA trend-gated.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Tirone Levels (John Tirone), per FreshForex's encyclopedia entry and
corroborated by MarketInOut and LuxAlgo's Tirone Levels indicator page
(all read via browser_exec this iteration, `web_search` DDGS/Yahoo backend
down again). The Midpoint Method divides the rolling range between the
highest high and lowest low over a lookback window into thirds:

    top_third    = HH - (HH - LL) / 3
    center       = LL + (HH - LL) / 2
    bottom_third = LL + (HH - LL) / 3

These act as dynamic support/resistance thirds within the recent trading
range -- conceptually similar in spirit to a Donchian channel, but with
TWO interior reference lines (top_third, center) rather than just the
channel extremes. This is a genuinely new indicator family for this
repo (0 prior Tirone Levels entries).

This iteration treats a close breaking above the rolling top_third level
as a breakout signal (price has cleared the upper third of its own recent
range -- a resistance breakout in Tirone's own intended support/resistance
role), gated by an SMA(trend_window) uptrend filter for regime
confirmation. Exit when close falls back below the center line (giving up
more than half the recent range) or a max_hold_days time-stop.

Signal logic
------------
- trend_long = close > SMA(trend_window).
- HH/LL = rolling max(high)/min(low) over `tirone_window` bars.
- top_third = HH - (HH-LL)/3; center = LL + (HH-LL)/2.
- Entry: close crosses above top_third AND trend_long.
- Exit: close crosses below center, trend filter breaks, or max_hold_days.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _tirone_levels(df: pd.DataFrame, tirone_window: int):
    hh = df["high"].rolling(tirone_window).max()
    ll = df["low"].rolling(tirone_window).min()
    top_third = hh - (hh - ll) / 3.0
    center = ll + (hh - ll) / 2.0
    return top_third, center


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    tirone_window: int = 20,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a 0/1 long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    top_third, center = _tirone_levels(df, tirone_window)

    breakout = (close > top_third) & (close.shift(1) <= top_third.shift(1))

    position = pd.Series(0.0, index=close.index)
    in_position = False
    entry_idx = -1
    for i in range(len(close)):
        if not in_position:
            if bool(breakout.iloc[i]) and bool(trend_long.iloc[i]):
                in_position = True
                entry_idx = i
        else:
            held = i - entry_idx
            below_center = close.iloc[i] < center.iloc[i] if not np.isnan(center.iloc[i]) else False
            if below_center or (not trend_long.iloc[i]) or held >= max_hold_days:
                in_position = False
        position.iloc[i] = 1.0 if in_position else 0.0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
