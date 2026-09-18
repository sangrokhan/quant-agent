"""Strategy: Larry Connors' 3-Day High/Low Method (mean reversion within
an established uptrend).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-001):
Per Larry Connors & Cesar Alvarez, "High Probability ETF Trading" (2009),
summarized at
https://www.quantifiedstrategies.com/larry-connors-3-day-high-low-method/
(read via browser_exec after browsing the site's free-strategy index --
web_search returned only generic guide pages, not this specific article):
Connors' own disclosed rule is:
  1. Today's close > 200-day SMA (established long-term uptrend)
  2. Today's close < 5-day SMA (short-term pullback within that uptrend)
  3. For 3 consecutive days (today and the prior two), BOTH the daily high
     AND the daily low are lower than the prior day's high/low (a genuine
     3-day "lower highs and lower lows" pullback structure)
  4. If all 3 conditions hold, buy at today's close.
  5. Exit when close crosses back above the 5-day SMA.

This is distinct from the already-tested Lower-Highs/Lower-Lows-3-Day
Reversal (2026-09-18-093/094 in this repo) via TWO added gates that
Connors' article makes central to the rule: (a) the 200-day SMA uptrend
filter (2026-09-18-093 had no long-term trend filter at all), and (b) the
5-day-SMA-based ENTRY confirmation (below the 5d SMA, not just below
yesterday's low) and adaptive EXIT (cross back above 5d SMA, rather than a
fixed N-day time-stop). Both changes are the source's own explicit
mechanism, not an invented variant.

Interface contract for validators (see validation/validators.py) and
grid_test.py: both generate_signals and generate_returns accept all
tunable parameters as keyword arguments.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    pullback_sma_window: int = 5,
    confirm_days: int = 3,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: close > SMA(trend_window) AND close < SMA(pullback_sma_window)
    AND for `confirm_days` consecutive days (inclusive of today), both
    high and low are strictly lower than the prior day's high/low.
    Exit: close crosses back above SMA(pullback_sma_window), or a
    max_hold_days time-stop backstop (Connors' own rule has no explicit
    time-stop; this repo's standard backstop guards against indefinite
    holds if the exit condition never re-triggers).
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    sma_trend = close.rolling(trend_window).mean()
    sma_pullback = close.rolling(pullback_sma_window).mean()

    lower_high = high < high.shift(1)
    lower_low = low < low.shift(1)
    lower_both = (lower_high & lower_low).fillna(False)
    # confirm_days consecutive days (today + prior confirm_days-1) all
    # satisfying lower_both.
    streak_ok = lower_both.rolling(confirm_days).sum() >= confirm_days

    uptrend = (close > sma_trend).fillna(False)
    pullback = (close < sma_pullback).fillna(False)

    entry_trigger = (uptrend & pullback & streak_ok).fillna(False)
    exit_trigger = (close > sma_pullback).fillna(False)

    in_position = False
    hold_days = 0
    pos_vals = [0] * len(close)
    entry_vals = entry_trigger.values
    exit_vals = exit_trigger.values
    for i in range(len(pos_vals)):
        if in_position:
            hold_days += 1
            if exit_vals[i] or hold_days >= max_hold_days:
                in_position = False
                pos_vals[i] = 0
                hold_days = 0
            else:
                pos_vals[i] = 1
        else:
            if entry_vals[i]:
                in_position = True
                hold_days = 1
                pos_vals[i] = 1
            else:
                pos_vals[i] = 0
    position = pd.Series(pos_vals, index=close.index, dtype=int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
