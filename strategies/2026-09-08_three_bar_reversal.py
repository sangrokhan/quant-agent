"""Strategy: Bullish Three-Bar Reversal (probe-bar low + confirmation close).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-124):
Per https://www.luxalgo.com/library/concept/three-bar-reversal/, a bullish
three-bar reversal is "the smallest complete turn a chart can print": bar1
continues an existing decline, bar2 makes the LOWEST LOW of the three-bar
sequence (the probe that defines a pivot), and bar3 closes back ABOVE
bar2's high (confirmation that the lower probe found no follow-through
selling). Entry on bar3's close; stop below bar2's low (the natural
structural invalidation level per the source: "if price trades back
through that pivot, the reversal premise is gone"); exit on the stop or a
max-hold time-stop (no explicit target given by the source -- treated as
tunable). An optional "downtrend context" filter (close below a trailing
SMA at bar1) is added per the source's own note that "location decides
whether any of it matters, since the identical sequence mid-range is scan
noise." First three-bar-reversal (bar-count, not candlestick-anatomy)
strategy in this repo -- distinct from candlestick-body patterns like
Hammer/Piercing Line/Morning Star already tested, since this uses purely
high/low bar-range geometry across 3 consecutive bars with no candle-body
requirements.

Signal logic
------------
- bar1 (2 days ago): part of a decline -- close < close 3 days ago (simple
  proxy for "continues the existing leg lower").
- bar2 (yesterday): low == rolling 3-bar minimum low (the probe/pivot).
- bar3 (today): close > bar2's high (confirmation).
- Optional trend filter: bar1's close < its trailing `trend_window`-day SMA
  (only take the reversal within an established downtrend/pullback, per
  the source's location-matters caveat).
- Entry: long at bar3's close when all conditions hold.
- Exit: close < bar2's low (stop triggered) OR max_hold_days elapses.
- Flat otherwise, long-only, one position at a time.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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
    trend_window: int = 20,
    use_trend_filter: bool = True,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, high, low = df["close"], df["high"], df["low"]

    # bar3 = today (i), bar2 = yesterday (i-1), bar1 = 2 days ago (i-2)
    bar2_low = low.shift(1)
    bar2_high = high.shift(1)
    bar1_close = close.shift(2)
    bar1_close_3ago = close.shift(3)  # close before bar1, to judge "declining into" the pattern

    is_lowest_of_three = bar2_low == pd.concat(
        [low.shift(1), low.shift(2), low.shift(3)], axis=1
    ).min(axis=1)
    declining_into = bar1_close < bar1_close_3ago
    confirmation = close > bar2_high

    sma = close.rolling(trend_window).mean()
    trend_ok = (bar1_close < sma.shift(2)) if use_trend_filter else pd.Series(True, index=close.index)

    entry = is_lowest_of_three.fillna(False) & declining_into.fillna(False) & confirmation.fillna(False) & trend_ok.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = None
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            hit_stop = close.iloc[i] < stop_price
            if hit_stop or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                stop_price = bar2_low.iloc[i]
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
