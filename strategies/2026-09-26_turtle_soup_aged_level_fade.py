"""Strategy: Turtle Soup failed-breakdown fade, WITH the source's disclosed
"aged level" filter (the specific element this repo's prior plain Turtle
Soup attempt, id 2026-09-04-076, omitted before being decisively rejected).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per Linda Bradford Raschke & Laurence Connors, "Street Smarts" (1995),
summarized at
https://plutux.ai/resources/trading-systems/turtle-soup-failed-breakout
(visited this iteration): a new N-day low (measured against the PRIOR bar's
rolling low, i.e. excluding today, matching the source's own Donchian-band
construction) that fails and closes back above that broken level the same or
next session is a tradable "trapped breakout seller" reversal -- but ONLY
when the level being broken is "at least four sessions old" (source's own
explicit qualifier for signal quality). This repo's earlier plain Turtle Soup
variant (2026-09-04-076) had no such age filter and was decisively rejected
across all assets; this is a direct, source-grounded addressal of that gap,
not a re-run of the same rule.

Signal logic
------------
- ``breakout_window``-day rolling low of ``close`` (or ``low``, configurable
  via ``use_low_for_level``), computed on data EXCLUDING today (i.e. shifted
  by 1) -- this is "the prior 20-day low" the source refers to.
- "Level age": the rolling low value must not have been set within the last
  ``min_level_age`` sessions (i.e. the rolling-low value hasn't changed in
  the last ``min_level_age`` bars) -- this is the source's own
  "the level should be at least four sessions old" qualifier.
- Sweep: today's low trades below that (aged) rolling-low level.
- Entry (long): the sweep bar's close, OR the very next bar's close, trades
  back above the broken level (source: "same or next session").
- Exit: a fixed short hold of ``max_hold_days`` bars (source: "one to four
  days", i.e. this is a fade/snap-back trade, not a trend position), or a
  stop-out if close re-crosses back below the sweep bar's own low (source:
  "stop just under the low of the failed break").

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
    breakout_window: int = 20,
    min_level_age: int = 4,
    max_hold_days: int = 3,
    use_low_for_level: bool = True,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"] if (use_low_for_level and "low" in df.columns) else close

    # Prior-bar rolling low (excludes today), matching the Donchian-style
    # "prior N-day low" the source describes.
    rolling_low_incl_today = low.rolling(breakout_window).min()
    level = rolling_low_incl_today.shift(1)

    # "Level age": how many bars since the rolling-low VALUE last changed
    # (i.e. since a fresh lower low was actually set). A small/stale change
    # count means the level has held for a while -- qualifies as "aged".
    level_changed = level != level.shift(1)
    # bars_since_change: count of consecutive bars where level stayed the same
    bars_since_change = pd.Series(0, index=level.index, dtype=int)
    counter = 0
    for i in range(len(level)):
        if bool(level_changed.iloc[i]) or pd.isna(level.iloc[i]):
            counter = 0
        else:
            counter += 1
        bars_since_change.iloc[i] = counter
    level_is_aged = bars_since_change >= min_level_age

    sweep = (low < level) & level_is_aged.fillna(False) & level.notna()
    # Recovery: close back above the broken level, same bar or next bar.
    recovered_same_bar = sweep & (close > level)
    recovered_next_bar = sweep.shift(1).fillna(False) & (close > level.shift(1))
    entry_signal = (recovered_same_bar | recovered_next_bar).fillna(False)

    # Stop level: the low of the sweep bar itself (track most recent sweep low
    # while a position is open, for the stop-out check).
    sweep_low = low.where(sweep)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_level = None
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            stopped_out = (stop_level is not None) and (close.iloc[i] < stop_level)
            if stopped_out or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                stop_level = None
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_position = True
                entry_idx = i
                # Use the most recent sweep low up to and including this bar
                # as the stop reference.
                recent_sweep_low = sweep_low.iloc[max(0, i - 1):i + 1].dropna()
                stop_level = recent_sweep_low.iloc[-1] if len(recent_sweep_low) else low.iloc[i]
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
