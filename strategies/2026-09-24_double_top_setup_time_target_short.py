"""Strategy: Bulkowski's Double Top Setup -- time-based target for shorting a
confirmed double top after a flat-base + straight-line run-up.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-139):
Per https://thepatternsite.com/dtsetup.html (Thomas Bulkowski, browser_exec):
for double tops preceded by a flat base/congestion region and a fast,
pause-free straight-line run-up (A -> B, where A is the swing low that
starts the trend and B is the first peak), the time it takes price to
decline from confirmation (C, the close below the valley between the two
peaks) back down to the launch price (D, approximately A's price level)
tends to be similar to, and usually LESS than, the AB rise time (source's
own numbers: 24-day average AB vs. 19-day average CD; 70% of qualifying
patterns that did return to the launch price did so in less time than the
AB move took).

This repo implements this as a SHORT, TIME-based-target strategy (distinct
from the already-tested percentage-target 2B Top short, 2026-09-24-*, and
from the already-tested Double Top / Adam-Eve breakout strategies): entry
(short) is the confirmation bar (close below the valley/neckline between
peaks B and a second peak near B), and exit is the FIRST of (a) close
reaches or drops below the launch price A (the time-based target
materialized), (b) `ab_days` (the AB rise's own duration, dynamically
measured per pattern) trading days have elapsed since confirmation without
reaching the target (source's own disclosed "use the AB time to project
from C" conservative time budget -- exit anyway once that budget expires,
regardless of price), or (c) price recovers back above the second peak's
high (thesis invalidated).

First TIME-based-exit double-top strategy in this repo (all prior double
top/2B strategies use price-percentage or trend/pattern-based exits, not a
dynamically-measured AB-duration time-stop).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series ({-1,0} position;
        -1 = short, 0 = flat)
    generate_returns(price_df, **params) -> pd.Series (daily strategy
        returns, position lagged by 1 day, no transaction costs here)
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


def _find_pivots(series: np.ndarray, window: int, mode: str):
    n = len(series)
    half = window // 2
    idx = []
    for i in range(half, n - half):
        w = series[i - half:i + half + 1]
        if mode == "high" and series[i] == w.max() and (w == series[i]).sum() == 1:
            idx.append(i)
        elif mode == "low" and series[i] == w.min() and (w == series[i]).sum() == 1:
            idx.append(i)
    return idx


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 9,
    max_peak_diff_pct: float = 0.03,
    min_run_pct: float = 0.08,
    max_time_stop_mult: float = 1.0,
) -> pd.Series:
    """Return a {-1,0} short/flat position series."""
    df = _prep(price_df)
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    n = len(close)

    swing_highs = _find_pivots(high, pivot_window, "high")
    swing_lows = _find_pivots(low, pivot_window, "low")
    swing_low_set = sorted(swing_lows)

    entries = {}  # entry_bar -> (launch_price, ab_days, invalidation_price)

    for k in range(len(swing_highs) - 1):
        b_idx, second_idx = swing_highs[k], swing_highs[k + 1]
        b_high, second_high = high[b_idx], high[second_idx]
        if b_high <= 0:
            continue
        diff_pct = abs(second_high - b_high) / b_high
        if diff_pct > max_peak_diff_pct:
            continue  # not a double-top-similar-peaks pair

        # Find A: the most recent swing low BEFORE b_idx.
        a_candidates = [i for i in swing_low_set if i < b_idx]
        if not a_candidates:
            continue
        a_idx = a_candidates[-1]
        a_price = low[a_idx]
        if a_price <= 0:
            continue
        ab_days = b_idx - a_idx
        run_pct = (b_high - a_price) / a_price
        if run_pct < min_run_pct or ab_days <= 0:
            continue  # require a real straight-line run-up

        # Find the valley (lowest low) between b_idx and second_idx -- the
        # confirmation trigger is close below this valley, occurring after
        # second_idx.
        if second_idx <= b_idx:
            continue
        valley_low = low[b_idx:second_idx + 1].min()

        for j in range(second_idx + 1, n):
            if close[j] < valley_low:
                if j not in entries:
                    entries[j] = (a_price, ab_days, second_high)
                break

    position = np.zeros(n, dtype=int)
    in_pos = False
    entry_idx = -1
    launch_price = np.inf
    time_budget = 0
    invalidation_price = np.inf

    for t in range(n):
        if not in_pos and t in entries:
            in_pos = True
            entry_idx = t
            launch_price, time_budget, invalidation_price = entries[t]
        if in_pos:
            position[t] = -1
            held = t - entry_idx
            hit_target = close[t] <= launch_price
            hit_stop = close[t] > invalidation_price
            hit_time = held >= max(1, round(time_budget * max_time_stop_mult))
            if hit_target or hit_stop or hit_time:
                in_pos = False

    return pd.Series(position, index=df.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs).

    Position is -1 while short; multiplying by daily returns means a price
    DROP while short produces a POSITIVE strategy return, matching a real
    short position's payoff.
    """
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
