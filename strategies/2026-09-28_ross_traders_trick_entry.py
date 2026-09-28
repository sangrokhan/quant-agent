"""Strategy: Joe Ross Trader's Trick Entry (TTE) on top of a Ross Hook /
1-2-3 setup -- an EARLIER entry than the hook's own breakout confirmation.

Hypothesis (source: https://forexsb.com/wiki/trading/tte, read 2026-09-28
via browser_exec):

"Once a Ross Hook or point 2 of 1-2-3 pattern is in place, we watch the
correction and want to buy a violation of the high of any of the first
three [bars] after the Ross Hook [point]... The trade can be initiated
after more than 3 bars only if a double or triple high/low forms... there
must be sufficient room between our entry price and the Rh point for us
to be able to cover costs and take at least some profit." TTE is
explicitly an EARLIER, pre-emptive entry relative to this repo's existing
Ross Hook strategy (2026-09-28-066/067), which enters only once the
secondary hook's own high is broken (waiting for full confirmation). TTE
instead enters on the violation of the high of ONE of the first few bars
following the hook's low point (before the hook's own high is broken),
trading the theory that large participants engineer moves toward
resting orders and an earlier entry captures more of the move while
still requiring sufficient room to the Rh level to cover costs. 0 prior
"Trader's Trick Entry"/"TTE" hits in strategies_index.jsonl -- distinct
timing mechanic layered on the same underlying pattern already tested.

Mechanical proxy (daily-bar, long-only, bullish continuation): reuses the
primary-1-2-3-then-hook detection from the existing Ross Hook strategy,
but changes ONLY the entry trigger and timing:
  1. Detect primary bullish 1-2-3 (L-H-L, P3 > P1) and its breakout above
     P2, same as the existing Ross Hook strategy.
  2. Detect the hook's LOW point (Rh, a swing low after the primary
     breakout) -- this is TTE's anchor point, not the hook's own high.
  3. TTE entry: within the first `tte_bars` bars after Rh, enter long on
     the first bar whose close exceeds the HIGH of any prior bar within
     that same window (a "violation" of an early post-Rh bar's high),
     subject to a minimum room requirement: the entry price must be at
     least `min_room_pct` below the eventual hook_top level implied by
     the primary leg's height (approximated as Rh + leg_height), ensuring
     "sufficient room... to cover costs."
  4. Stop: Rh (source: "initial stop... on the opposite side of the
     bar" -- approximated here as the hook low itself, consistent with
     the sibling Ross Hook strategy's stop placement).
  5. Exit: stop hit, target (entry + target_r_multiple * leg_height)
     reached, or max_hold_days time-stop.

Interface contract (see validation/validators.py and validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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
    pivot_window: int = 7,
    hook_lookback: int = 25,
    tte_bars: int = 3,
    min_room_pct: float = 0.01,
    target_r_multiple: float = 1.5,
    max_hold_days: int = 25,
) -> pd.Series:
    """Return a {0,1} long/flat position series for bullish TTE entries."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    high_pivots = _find_pivots(high, pivot_window)
    low_pivots = _find_pivots(low, pivot_window)

    swing_idx = []
    for i in range(len(df)):
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

    primaries = []
    for k in range(len(alt_swings) - 2):
        p1, p2, p3 = alt_swings[k], alt_swings[k + 1], alt_swings[k + 2]
        if p1[1] == "L" and p2[1] == "H" and p3[1] == "L":
            if p3[2] > p1[2] and p2[2] > p1[2]:
                primaries.append({"p1": p1[2], "p2_idx": p2[0], "p2": p2[2]})

    c_arr = close.to_numpy()
    h_arr = high.to_numpy()
    n = len(c_arr)

    setups = []
    for prim in primaries:
        p2_idx = prim["p2_idx"]
        for i in range(p2_idx, min(p2_idx + hook_lookback, n)):
            if c_arr[i] > prim["p2"]:
                setups.append({"breakout_idx": i, "primary": prim})
                break

    # For each primary breakout, find the hook's low (Rh), then look for a
    # TTE entry (violation of an early post-Rh bar's high) within tte_bars.
    entries = []
    low_arr = low.to_numpy()
    for s in setups:
        b_idx = s["breakout_idx"]
        prim = s["primary"]
        leg_height = prim["p2"] - prim["p1"]
        search_end = min(b_idx + 25, n)
        rh_idx = None
        rh_price = None
        for i in range(b_idx + 1, search_end):
            if low_pivots.iloc[i] == -1 and low_arr[i] > prim["p1"]:
                rh_idx = i
                rh_price = low_arr[i]
                break
        if rh_idx is None:
            continue
        window_end = min(rh_idx + tte_bars, n)
        for i in range(rh_idx + 1, window_end):
            # violation of the high of a prior bar within the window
            for j in range(rh_idx, i):
                if c_arr[i] > h_arr[j]:
                    hook_top_approx = rh_price + leg_height
                    room = (hook_top_approx - c_arr[i]) / c_arr[i] if c_arr[i] > 0 else 0
                    if room >= min_room_pct:
                        entries.append({
                            "entry_idx": i,
                            "stop": rh_price,
                            "leg_height": leg_height,
                        })
                    break
            if entries and entries[-1]["entry_idx"] == i:
                break

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = 0.0
    target_price = 0.0
    used = set()

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if c_arr[i] < stop_price or c_arr[i] >= target_price or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            for e_idx, e in enumerate(entries):
                if e_idx in used:
                    continue
                if i != e["entry_idx"]:
                    continue
                in_position = True
                entry_idx = i
                stop_price = e["stop"]
                target_price = c_arr[i] + target_r_multiple * e["leg_height"]
                used.add(e_idx)
                position.iloc[i] = 1
                break
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
