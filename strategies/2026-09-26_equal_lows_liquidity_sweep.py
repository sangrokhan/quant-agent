"""Strategy: Equal-Lows Liquidity Sweep Reversal (double-bottom stop-hunt).

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-26-033):
Per tradingplan.io's "Liquidity Sweep Reversal: The Complete Trading
Strategy Guide" (ICT/liquidity-sweep concepts, read via browser_exec --
first "liquidity sweep"/"equal lows"/"CHoCH" hit in this repo's
knowledge base). Source's own disclosed rule explicitly distinguishes a
sweep of a SINGLE prior low (a "less significant" one-off stop run) from
a sweep of EQUAL LOWS -- two or more nearby lows close in price to each
other, which "takes out a larger cluster of stops than a sweep of a
single low, generating more institutional liquidity and a more
significant reversal". This repo's existing single-swing-low sweep
constructions (Turtle Soup, id=2026-09-04-076, next-bar close-back-above;
Swing Failure Pattern, id=2026-09-09-087, same-bar wick-and-reject) were
BOTH decisively rejected on full-sample Sharpe/TC-survival. This
iteration tests the source's own specific refinement -- requiring TWO
distinct local lows within a tight tolerance of each other (an "equal
lows" liquidity pool) before treating a subsequent sweep-and-reclaim as
a valid setup -- as a higher-selectivity variant that trades far less
often but (per the source's stated rationale) with higher conviction per
trade. Distinct construction from both 2026-09-04-076 and 2026-09-09-087
since it requires the EQUAL-LOWS precondition (a genuine liquidity-pool
concept), not just any single prior low.

Signal logic
------------
- Over a trailing `lookback_window`, find local swing lows (a bar whose
  low is the minimum within a small `pivot_window` neighborhood).
- Two swing lows within `equal_low_tolerance` (relative pct) of each
  other, separated by at least `min_separation` bars, define an
  "equal lows" liquidity level = the lower of the two.
- Sweep + reclaim: today's low < equal_lows_level (sweeps below the
  pool), AND today's close > equal_lows_level (same-bar reclaim/
  rejection -- source's CHoCH proxy at daily-bar resolution).
- Entry: next bar's open (this repo's generate_signals contract shifts
  exposure by 1 bar in generate_returns, so signals fire the trigger
  bar and the actual P&L starts the following bar, consistent with
  every other strategy file in this repo).
- Exit: risk:reward target (`rr_target` x the entry-to-stop distance,
  where stop = the sweep bar's own low minus a small buffer) is hit, OR
  a `max_hold_days` time-stop, whichever comes first. Long-only.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
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


def _find_swing_lows(low: pd.Series, pivot_window: int) -> pd.Series:
    """Boolean mask: True where `low` is the minimum within a centered
    window of +/- pivot_window bars (a local swing low pivot)."""
    roll_min = low.rolling(2 * pivot_window + 1, center=True).min()
    return (low == roll_min).fillna(False)


def _equal_lows_level(
    low: pd.Series,
    pivot_window: int,
    lookback_window: int,
    equal_low_tolerance: float,
    min_separation: int,
) -> pd.Series:
    """For each bar t, look back over `lookback_window` prior bars for
    TWO swing-low pivots within `equal_low_tolerance` of each other
    (separated by >= min_separation bars); return the lower of the two
    as the "equal lows" liquidity level at t (NaN if no such pair
    exists in the lookback). Strictly uses data up to t-1 (no
    look-ahead: the pivot mask itself uses a centered window, but we
    only reference pivots whose centered window is fully in the past
    relative to the CURRENT evaluation bar via the shift below)."""
    is_pivot = _find_swing_lows(low, pivot_window)
    n = len(low)
    low_vals = low.to_numpy()
    pivot_vals = is_pivot.to_numpy()
    levels = np.full(n, np.nan)

    for t in range(n):
        start = max(0, t - lookback_window)
        # only consider pivots that are fully resolved (pivot_window bars
        # before t, so the centered rolling-min window doesn't peek ahead
        # of t-1)
        end = t - pivot_window
        if end <= start:
            continue
        pivot_idxs = [i for i in range(start, end) if pivot_vals[i]]
        if len(pivot_idxs) < 2:
            continue
        best_level = None
        for a in range(len(pivot_idxs)):
            for b in range(a + 1, len(pivot_idxs)):
                i, j = pivot_idxs[a], pivot_idxs[b]
                if abs(i - j) < min_separation:
                    continue
                li, lj = low_vals[i], low_vals[j]
                if lj == 0:
                    continue
                rel_diff = abs(li - lj) / lj
                if rel_diff <= equal_low_tolerance:
                    level = min(li, lj)
                    if best_level is None or level > best_level:
                        best_level = level  # prefer the highest (most recent-relevant) qualifying pool
        if best_level is not None:
            levels[t] = best_level

    return pd.Series(levels, index=low.index)


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 3,
    lookback_window: int = 60,
    equal_low_tolerance: float = 0.005,
    min_separation: int = 5,
    rr_target: float = 2.0,
    stop_buffer_pct: float = 0.002,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    low = df["low"]
    close = df["close"]

    equal_lows_level = _equal_lows_level(
        low, pivot_window, lookback_window, equal_low_tolerance, min_separation
    )

    swept = (low < equal_lows_level) & close.notna()
    reclaimed = close > equal_lows_level
    trigger = (swept & reclaimed).fillna(False)

    n = len(df)
    close_vals = close.to_numpy()
    low_vals = low.to_numpy()
    trigger_vals = trigger.to_numpy()
    pos_vals = np.zeros(n, dtype=int)

    in_pos = False
    hold_count = 0
    entry_price = 0.0
    stop_price = 0.0
    target_price = 0.0

    for i in range(n):
        if in_pos:
            hold_count += 1
            hit_target = close_vals[i] >= target_price
            hit_stop = low_vals[i] <= stop_price
            if hit_target or hit_stop or hold_count >= max_hold_days:
                in_pos = False
                pos_vals[i] = 0
            else:
                pos_vals[i] = 1
        else:
            if bool(trigger_vals[i]):
                in_pos = True
                hold_count = 0
                entry_price = close_vals[i]
                stop_price = low_vals[i] * (1 - stop_buffer_pct)
                risk = entry_price - stop_price
                target_price = entry_price + rr_target * risk
                pos_vals[i] = 1
            else:
                pos_vals[i] = 0

    return pd.Series(pos_vals, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    pivot_window: int = 3,
    lookback_window: int = 60,
    equal_low_tolerance: float = 0.005,
    min_separation: int = 5,
    rr_target: float = 2.0,
    stop_buffer_pct: float = 0.002,
    max_hold_days: int = 15,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        pivot_window=pivot_window,
        lookback_window=lookback_window,
        equal_low_tolerance=equal_low_tolerance,
        min_separation=min_separation,
        rr_target=rr_target,
        stop_buffer_pct=stop_buffer_pct,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
