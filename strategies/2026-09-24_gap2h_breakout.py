"""Strategy: Gap 2H Pattern (Michael Harris via Paolo Pezzutti, Traders.com;
long-only continuation).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/Gap2H.html (Thomas Bulkowski's
summary of Paolo Pezzutti's Traders.com article on Michael Harris's Gap 2H
pattern, browser_exec fallback -- web_search's DDGS backend cannot extract
this domain). Source's own disclosed identification rules and precise
numeric trading tactic:

    "The pattern is composed of three bars, a gap followed by two higher
    highs and two higher lows. Price gap: Look for price to gap higher.
    Yesterday's low price is above the prior day's high, forming a gap.
    Higher high: The third bar in the pattern makes a higher high. Higher
    low: The third bar in the pattern makes a higher low, but it remains
    below the 2nd bar's high... The article says to use a 7% profit
    target and 7% stop loss, which I tested. He also recommends that the
    position be sold if the gap is closed. I tested a stop order, as a
    close below the bottom of the pattern (upward breakout)..."

NOTE: source's own disclosed stats for this pattern are WEAK (rank 21/23
among small patterns, 34% break-even failure rate for upward breakouts,
53% price-target hit rate) -- among the weakest priors this repo has
sourced. It is tested anyway BECAUSE it has an unusually precise,
fully-specified numeric trading rule directly from a named published
source (Michael Harris via Pezzutti's Traders.com article, as opposed to
Bulkowski's own qualitative "Measure Rule" used in most other patterns in
this repo) -- specifically the disclosed fixed 7%/7% target/stop, which is
a genuinely different exit mechanism from every prior chart-pattern
strategy in this repo (measure-rule targets, trailing stops, or
percentage-of-height targets).

First "Gap 2H" strategy in this repo (0 prior index hits) -- distinct via
its compact exactly-3-bar gap-plus-two-higher-highs/lows geometry and its
fixed-percentage (not pattern-height-scaled) target/stop.

Signal logic (numeric proxy for the source's precise 3-bar rule and its
own disclosed 7%/7% trading tactic)
------------------------------------------------------------------------
1. For each 3-bar window [i-2, i-1, i]:
   - gap: low[i-1] > high[i-2] (source: "yesterday's low price is above
     the prior day's high").
   - higher high: high[i] > high[i-1].
   - higher low: low[i] > low[i-1] AND low[i] < high[i-1] (source: "it
     remains below the 2nd bar's high").
   - Continuation/trend-with filter (source: pattern acts as continuation
     72% of the time, "trade with the trend"): close at i-2 above its own
     SMA(trend_lookback) (uptrend precondition -- long-only continuation
     scope for this strategy).
2. Confirmation/entry: source's own "wait for price to close above the
   top of the pattern" -- pattern top = max(high[i-2], high[i-1], high[i]).
   Long entry on the first subsequent bar whose close exceeds that top.
3. Exit: source's own disclosed fixed rule -- 7% profit target
   (`target_pct`) and 7% stop loss (`stop_pct`) from the entry price, OR a
   max_hold_days time-stop (added robustness stop, source doesn't specify
   a max hold), whichever comes first. (Gap-closed exit from the source
   is approximated by the stop-loss, since a fixed 7% stop from entry
   price is close to the pattern's own bottom in most cases.)

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
    trend_lookback: int = 50,
    target_pct: float = 0.07,
    stop_pct: float = 0.07,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series for Gap 2H completions."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]
    high_arr = high.to_numpy()
    low_arr = low.to_numpy()
    close_arr = close.to_numpy()
    n = len(close_arr)

    sma_trend = close.rolling(trend_lookback).mean().to_numpy()

    patterns = []  # (pattern_top,)
    for i in range(2, n):
        i2, i1 = i - 2, i - 1
        if not (low_arr[i1] > high_arr[i2]):
            continue  # gap up
        if not (high_arr[i] > high_arr[i1]):
            continue  # higher high
        if not (low_arr[i] > low_arr[i1] and low_arr[i] < high_arr[i1]):
            continue  # higher low, below 2nd bar's high
        if np.isnan(sma_trend[i2]) or close_arr[i2] <= sma_trend[i2]:
            continue  # uptrend precondition

        pattern_top = max(high_arr[i2], high_arr[i1], high_arr[i])
        patterns.append((i, pattern_top))

    entries = {}
    for pattern_end, pattern_top in patterns:
        for j in range(pattern_end + 1, n):
            if close_arr[j] > pattern_top:
                if j not in entries:
                    entries[j] = None
                break

    position = np.zeros(n, dtype=int)
    in_pos = False
    entry_idx = -1
    entry_price = np.nan
    target_price = np.inf
    stop_price = -np.inf

    for t in range(n):
        if not in_pos and t in entries:
            in_pos = True
            entry_idx = t
            entry_price = close_arr[t]
            target_price = entry_price * (1 + target_pct)
            stop_price = entry_price * (1 - stop_pct)
        if in_pos:
            position[t] = 1
            held = t - entry_idx
            hit_target = close_arr[t] >= target_price
            hit_stop = close_arr[t] <= stop_price
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
