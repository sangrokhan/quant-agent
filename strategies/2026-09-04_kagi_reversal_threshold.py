"""Strategy: Kagi chart thick/thin line-flip reversal-threshold trend follower.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-137):
Per tradejini.com's Kagi chart guide, a Kagi line ignores time and only
plots a new vertical segment when price reverses from the prior swing
extreme by more than a fixed threshold (a percentage of price, in the
classic construction). The line is drawn "thick" (yang, bullish) while
price is making new highs beyond the prior high-water mark since the last
reversal, and flips to "thin" (yin, bearish) once price reverses down
past the reversal threshold below the last swing high (or vice versa).
The source's own trading rule: thick lines signal bullish control (long
bias), thin lines signal bearish control; the flip point itself (yin->yang
transition, a "waist") is the systematic entry trigger, the reverse flip
(yang->yin, a "shoulder") is the exit trigger. This is the first Kagi/
point-and-figure-style noise-filtered reversal-threshold system tested in
this repo (distinct from ATR-based trailing stops and from the Fractal
5-bar swing-point system -- Kagi's swing points are defined by a
percentage price-move threshold with no fixed lookback window at all).

Signal logic
------------
- Track a running Kagi state: current direction (up/down), and the
  extreme price reached in that direction since the last reversal.
- While direction is "up": if close makes a new high vs the running
  extreme, extend (stay bullish/thick). If close falls more than
  `reversal_pct` below the running extreme, flip to "down" (thin) and
  reset the extreme to that close.
- Mirror logic for direction "down".
- Entry (long): direction flips from down to up (a "waist", per source).
- Exit: direction flips from up to down (a "shoulder"), OR max_hold_days
  time-stop.
- Long-only, flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _kagi_direction(close: pd.Series, reversal_pct: float) -> pd.Series:
    """Return a Series of +1 (up/thick) / -1 (down/thin) Kagi direction,
    computed causally bar-by-bar (no look-ahead)."""
    n = len(close)
    direction = pd.Series(0, index=close.index, dtype=int)
    if n == 0:
        return direction

    # Initialize using the first bar; direction undefined until a
    # reversal has actually happened, so seed as "up" from bar 0.
    cur_dir = 1
    extreme = close.iloc[0]
    direction.iloc[0] = cur_dir

    for i in range(1, n):
        c = close.iloc[i]
        if cur_dir == 1:
            if c > extreme:
                extreme = c
            elif c < extreme * (1 - reversal_pct):
                cur_dir = -1
                extreme = c
        else:
            if c < extreme:
                extreme = c
            elif c > extreme * (1 + reversal_pct):
                cur_dir = 1
                extreme = c
        direction.iloc[i] = cur_dir
    return direction


def generate_signals(
    price_df: pd.DataFrame,
    reversal_pct: float = 0.04,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(df)

    direction = _kagi_direction(close, reversal_pct)
    direction_prev = direction.shift(1)

    entry_trigger = (direction == 1) & (direction_prev == -1)
    exit_trigger = (direction == -1) & (direction_prev == 1)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            et = bool(exit_trigger.iloc[i]) if pd.notna(exit_trigger.iloc[i]) else False
            if et or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            entered = bool(entry_trigger.iloc[i]) if pd.notna(entry_trigger.iloc[i]) else False
            if entered:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    reversal_pct: float = 0.04,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(df, reversal_pct=reversal_pct, max_hold_days=max_hold_days)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
