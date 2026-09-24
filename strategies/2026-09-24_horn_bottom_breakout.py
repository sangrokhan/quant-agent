"""Strategy: Bulkowski Horn Bottom (H-shaped twin-spike reversal, long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/hornb.html (Thomas Bulkowski,
browser_exec fallback -- web_search's DDGS backend cannot extract this
domain). Source's own disclosed identification rules and statistics:

    "Horn bottoms are H-shaped chart patterns... discovered by Thomas
    Bulkowski in 1998... Price trend: Downward leading to the pattern.
    Shape: Looks like an inverted steer's horn, two parallel price spikes
    separated by a week [bar]. Spikes: ... They should plummet below the
    surrounding price landscape, including the middle week [bar].
    Confirmation: The pattern confirms as valid when price closes above
    the highest price in the 3-week [3-bar] pattern... Overall performance
    rank (1 is best): 2 out of 3 (weekly scale). Break even failure rate:
    6%. Average rise: 59%. Percentage meeting price target: 74%."

A 6% break-even failure rate and rank 2/3 are among the strongest
(lowest-failure, best-rank) disclosed statistics of any Bulkowski pattern
sourced in this repo. IMPORTANT DISCLOSED CAVEAT: the source explicitly
states these stats are gathered from the WEEKLY scale ("weekly charts show
better performance over those appearing on the dailies") -- this repo's
established convention (see e.g. 2026-09-24_pipe_bottom_breakout.py, which
tested a similar daily/weekly scale-mismatch pattern and was rejected) is
to test Bulkowski's daily-bar-agnostic patterns on daily bars anyway as a
disclosed deviation, consistent with every other chart-pattern strategy in
this repo (all trade on daily OHLCV via data/loaders.py). This is flagged
explicitly as a feasibility caveat rather than silently ignored.

First "Horn Bottom" strategy in this repo (0 prior index hits) -- distinct
from every other reversal pattern tested via its precise, narrow 3-bar
H-shape geometry (two roughly-equal-depth spikes flanking a middle bar
that is itself higher than both, all three sitting below the surrounding
price landscape) rather than a wider multi-bar bowl/valley/shoulder
structure.

Signal logic (numeric proxy for the source's qualitative H-shape and its
own disclosed Measure Rule target-exit test)
------------------------------------------------------------------------
1. For each 3-bar window [i-2, i-1, i] of daily lows:
   - left_spike = low[i-2], middle = low[i-1], right_spike = low[i]
   - H-shape condition: middle > left_spike AND middle > right_spike
     (source: "two parallel spikes separated by a [bar]" -- the middle bar
     is NOT part of either spike, it sits higher).
   - "Plummet below the surrounding landscape": both spikes must be below
     their own trailing `surround_lookback`-bar rolling-min low
     (surround_tolerance allows near-ties), i.e. these are genuine local
     depth extremes, not just any 3-bar dip.
   - Downtrend precondition (source: "price trend downward leading to the
     pattern"): close at i-2 is below its own SMA(trend_lookback).
2. Confirmation: the highest HIGH in the 3-bar pattern window is the
   pattern top. Entry (long) on the first subsequent bar whose close
   exceeds that pattern top (source's own "confirms as valid when price
   closes above the highest price in the pattern").
3. Exit: source's own disclosed target-exit backtest methodology --
   height = pattern_top - min(left_spike, right_spike), target = pattern
   top + height * target_multiple (source used 2x height in its own
   height-exit test), OR close falls back below the lower of the two
   spikes (stop-loss, source's own "stop loss order a penny below the
   lower of the 3-bar horn pattern"), OR a max_hold_days time-stop,
   whichever comes first.

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


def generate_signals(
    price_df: pd.DataFrame,
    surround_lookback: int = 20,
    surround_tolerance: float = 0.0,
    trend_lookback: int = 50,
    target_multiple: float = 2.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series for Horn Bottom completions."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]
    high_arr = high.to_numpy()
    low_arr = low.to_numpy()
    close_arr = close.to_numpy()
    n = len(close_arr)

    sma_trend = close.rolling(trend_lookback).mean().to_numpy()
    rolling_min_low = low.rolling(surround_lookback).min().to_numpy()

    patterns = []  # (pattern_top, target_price, stop_price, confirm_search_start)
    for i in range(max(2, surround_lookback), n):
        left_idx, mid_idx, right_idx = i - 2, i - 1, i
        left_spike, middle, right_spike = low_arr[left_idx], low_arr[mid_idx], low_arr[right_idx]

        if not (middle > left_spike and middle > right_spike):
            continue

        # "plummet below the surrounding price landscape": both spikes
        # below their own trailing rolling-min low (allow small tolerance).
        surround_left = rolling_min_low[left_idx]
        surround_right = rolling_min_low[right_idx]
        if np.isnan(surround_left) or np.isnan(surround_right):
            continue
        if left_spike > surround_left * (1 + surround_tolerance):
            continue
        if right_spike > surround_right * (1 + surround_tolerance):
            continue

        # downtrend precondition
        if np.isnan(sma_trend[left_idx]) or close_arr[left_idx] >= sma_trend[left_idx]:
            continue

        pattern_top = max(high_arr[left_idx], high_arr[mid_idx], high_arr[right_idx])
        lower_spike = min(left_spike, right_spike)
        height = pattern_top - lower_spike
        if height <= 0:
            continue
        target_price = pattern_top + height * target_multiple
        stop_price = lower_spike

        patterns.append((right_idx, pattern_top, target_price, stop_price))

    # Assign entries: first bar after pattern completion (right_idx) whose
    # close exceeds pattern_top confirms and triggers entry on that bar.
    entries = {}
    for right_idx, pattern_top, target_price, stop_price in patterns:
        for j in range(right_idx + 1, n):
            if close_arr[j] > pattern_top:
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
