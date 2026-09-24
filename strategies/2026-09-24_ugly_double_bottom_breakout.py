"""Strategy: Bulkowski Ugly Double Bottom (bullish reversal, long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/udb.html (Thomas Bulkowski,
browser_exec fallback -- web_search's DDGS backend cannot extract this
domain). Source's own disclosed identification rules and statistics:

    "Think of an ugly double bottom as a double bottom in which the
    second bottom is significantly higher than the first... Shape: Looks
    like a double bottom with unequal bottoms. The second bottom should
    be between 5% and 15% higher than the first, and a consecutive minor
    low (no intervening low)... Breakout: Upward when price closes above
    the highest high between the two bottoms. Confirmation: The pattern
    confirms as valid when price closes above the peak between the two
    bottoms... Overall rank for up breakouts: 23 out of 41. Break even
    failure rate: 15%. Average rise: 41%."

This is the SAME "double bottom" family already tested and REJECTED once
in this repo (2026-09-08-101, per this repo's own knowledge base:
"generic Double Bottom... no disclosed numeric tolerances") and again as
Eve & Eve Double Bottom (2026-09-24-105, rejected). This "Ugly" variant is
distinct enough to test independently because it has THE OPPOSITE
numeric constraint from Bulkowski's classic double bottoms: instead of
requiring the two bottoms to be roughly EQUAL (Eve & Eve's disclosed 0-6%
tolerance), the Ugly variant explicitly REQUIRES INEQUALITY -- the second
bottom must be 5-15% HIGHER than the first (a rising-low structure, not a
flat "W"). This is a genuinely different, precisely-disclosed numeric
shape from every double-bottom variant already tested in this repo.

First "Ugly Double Bottom" strategy in this repo (0 prior index hits).

Signal logic (numeric proxy for the source's qualitative rising-unequal-
bottoms shape and confirmation rule)
------------------------------------------------------------------------
1. Swing pivot detection: same rolling-window fractal test used elsewhere
   in this repo to find alternating swing lows (bottoms)/highs (the
   intervening peak) over `pivot_window`.
2. For each pair of consecutive swing lows (first bottom at index a,
   second bottom at index b, a < b, with exactly one intervening swing
   high at index c between them -- "a consecutive minor low, no
   intervening low"): the "ugly" condition is second_low's price exceeds
   first_low's price by between `min_second_excess_pct` and
   `max_second_excess_pct` (source's own disclosed 5%-15% window).
3. Confirmation/entry: source's own "closes above the peak between the
   two bottoms" -- the intervening peak (swing high c). Long entry on the
   first subsequent bar whose close exceeds that peak.
4. Exit: source's own Measure Rule (height = peak_price - first_bottom,
   target = breakout_price + height * target_pct, source's own disclosed
   63% "percentage meeting price target"), OR close falls back below the
   second (higher) bottom (failed breakout, stop-loss), OR a
   max_hold_days time-stop, whichever comes first.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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


def _find_pivots(series: pd.Series, window: int) -> pd.Series:
    n = len(series)
    pivots = pd.Series(0, index=series.index, dtype=int)
    half = window // 2
    vals = series.values
    for i in range(half, n - half):
        window_vals = vals[i - half: i + half + 1]
        if vals[i] == window_vals.max() and (window_vals == vals[i]).sum() == 1:
            pivots.iloc[i] = 1
        elif vals[i] == window_vals.min() and (window_vals == vals[i]).sum() == 1:
            pivots.iloc[i] = -1
    return pivots


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 9,
    min_second_excess_pct: float = 0.05,
    max_second_excess_pct: float = 0.15,
    target_pct: float = 0.63,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series for Ugly Double Bottom completions."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]
    close_arr = close.to_numpy()
    n = len(close_arr)

    high_pivots = _find_pivots(high, pivot_window)
    low_pivots = _find_pivots(low, pivot_window)

    swing_idx = []
    for i in range(n):
        if high_pivots.iloc[i] == 1:
            swing_idx.append((i, "H", float(high.iloc[i])))
        if low_pivots.iloc[i] == -1:
            swing_idx.append((i, "L", float(low.iloc[i])))
    swing_idx.sort(key=lambda x: x[0])

    alt_swings = []
    for s in swing_idx:
        if alt_swings and alt_swings[-1][1] == s[1]:
            if s[1] == "H" and s[2] > alt_swings[-1][2]:
                alt_swings[-1] = s
            elif s[1] == "L" and s[2] < alt_swings[-1][2]:
                alt_swings[-1] = s
        else:
            alt_swings.append(s)

    entries = {}
    for k in range(len(alt_swings) - 2):
        a, c, b = alt_swings[k], alt_swings[k + 1], alt_swings[k + 2]
        if not (a[1] == "L" and c[1] == "H" and b[1] == "L"):
            continue
        first_low, peak, second_low = a[2], c[2], b[2]
        if first_low <= 0:
            continue
        excess = (second_low - first_low) / first_low
        if not (min_second_excess_pct <= excess <= max_second_excess_pct):
            continue

        b_idx = b[0]
        height = peak - first_low
        if height <= 0:
            continue
        target_price = peak + height * target_pct
        stop_price = second_low

        for j in range(b_idx + 1, n):
            if close_arr[j] > peak:
                if j not in entries:
                    entries[j] = (target_price, stop_price)
                break

    position = np.zeros(n, dtype=int)
    in_pos = False
    entry_idx = -1
    target_price = np.inf
    stop_price = -np.inf

    for t in range(n):
        if not in_pos and t in entries:
            in_pos = True
            entry_idx = t
            target_price, stop_price = entries[t]
        if in_pos:
            position[t] = 1
            held = t - entry_idx
            hit_target = close_arr[t] >= target_price
            hit_stop = close_arr[t] < stop_price
            if hit_target or hit_stop or held >= max_hold_days:
                in_pos = False

    return pd.Series(position, index=close.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
