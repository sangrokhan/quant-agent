"""Strategy: Turtle Soup — fade the failed 20-day-low breakdown, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-076):
The classic Turtle Soup pattern (Linda Bradford Raschke / Laurence Connors,
1995, later popularized as "ICT Turtle Soup"): price makes a new N-day low
(the same Donchian-style rolling extreme the original Turtle traders used
as a breakout ENTRY signal), then FAILS to continue lower and reverses back
above that level -- a false breakout / stop-hunt. Long entry: close breaks
below the rolling N-day low, then the very next close moves back above
that same N-day-low level, signaling the breakdown failed. Exit after a
fixed holding period or when close crosses back below the entry-day low
(stop). Explicitly the INVERSE of a trend-following Donchian breakout
(already tested at 2026-09-03-008/2026-09-04-054, which trade WITH the
breakout direction) -- this fades it. Sources note this is a genuinely
counter-trend/mean-reversion pattern that works better in
consolidation/range-bound conditions than in strong trends.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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
    lookback: int = 20,
    max_hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: close(t-1) < rolling_low(t-1) (a new N-day-low close occurred
    yesterday, using the PRIOR bar's rolling low so no lookahead) AND
    close(t) crosses back above that same rolling low level (the failed
    breakdown reverses). Exit after ``max_hold_days`` bars, or earlier if
    close falls back below the entry-day's low (stop).
    """
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]

    rolling_low = low.rolling(lookback).min()
    # The N-day-low level as of the PRIOR bar (the level that was broken).
    prior_level = rolling_low.shift(1)

    broke_down_yesterday = close.shift(1) < prior_level.shift(1)
    reversed_today = close > prior_level

    entry_trigger = broke_down_yesterday & reversed_today

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = None
    stop_level = None
    for i in range(len(df)):
        if in_position:
            days_held = i - entry_idx
            stopped_out = close.iloc[i] < stop_level if stop_level is not None else False
            if days_held >= max_hold_days or stopped_out:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            trig = entry_trigger.iloc[i]
            if bool(trig) if not pd.isna(trig) else False:
                in_position = True
                entry_idx = i
                stop_level = low.iloc[i]
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
