"""Strategy: Ross Hook trend-continuation entry (Joe Ross, via a bullish
1-2-3 breakout followed by a smaller secondary 1-2-3 "hook").

Hypothesis (source: https://fxopen.com/blog/en/how-to-trade-with-a-ross-hook-pattern/,
read 2026-09-28 via browser_exec):

The Ross Hook (Joe Ross) is a trend-CONTINUATION pattern built on top of
the classic 1-2-3 reversal structure (already tested in this repo as a
reversal entry -- 2026-09-11-022/025, 2026-09-18-090/091 -- entering on
the initial 1-2-3 neckline breakout itself). The Ross Hook is
mechanically DIFFERENT: it fires AFTER an initial 1-2-3 breakout has
already occurred and trended, when price retraces and forms a smaller,
SECONDARY 1-2-3-shaped "hook" during that retracement/consolidation --
the breakout of THIS secondary hook (not the original 1-2-3) is the
entry signal, used specifically to add to or re-enter an already-
established trend rather than to call the initial reversal. Source's own
disclosed rules: "the breakout of this pattern [signals] an entry...
stop losses placed just beyond the lowest point of the hook... measuring
the distance from the start of the 1-2-3 point to the Ross Hook's peak"
for a target. 0 prior "Ross Hook" hits in strategies_index.jsonl --
distinct continuation-vs-reversal mechanic from the already-tested plain
1-2-3 pattern.

Mechanical proxy (daily-bar swing-pivot scaffolding, long-only, bullish
case): reuses a fractal-pivot detector.
  1. Detect swing pivots via a centered rolling window.
  2. Primary bullish 1-2-3: P1 = a confirmed swing low (downtrend
     exhaustion), P2 = the next swing high (P2 > P1, recovery rally),
     P3 = the next swing low that stays ABOVE P1 (does not undercut the
     original low -- confirms the 1-2-3 structure per source's own
     "point 3 should not exceed [undercut] the height of point 1" rule).
  3. Primary breakout: close crosses above P2 (the initial 1-2-3
     breakout) -- this alone is NOT the entry (that's the already-tested
     reversal strategy); it just anchors the subsequent search for a hook.
  4. Ross Hook (secondary, smaller 1-2-3): after the primary breakout,
     look within hook_lookback bars for a secondary swing high
     (hook_top) followed by a secondary swing low (hook_bottom, staying
     above P3/the primary breakout level) followed by price breaking
     back above hook_top -- this secondary breakout is the actual entry.
  5. Stop: hook_bottom (source: "just beyond the lowest point of the
     hook"). Target: hook_top + target_r_multiple * (P2 - P1) (source's
     own "measure from the start of the 1-2-3 to the hook's peak" idea,
     approximated via the primary leg's height). Time-stop:
     max_hold_days.

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
    pivot_window: int = 9,
    hook_lookback: int = 25,
    target_r_multiple: float = 1.0,
    max_hold_days: int = 25,
) -> pd.Series:
    """Return a {0,1} long/flat position series for bullish Ross Hook entries."""
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

    # Find primary bullish 1-2-3 structures: L(P1)-H(P2)-L(P3, P3 > P1).
    primaries = []
    for k in range(len(alt_swings) - 2):
        p1, p2, p3 = alt_swings[k], alt_swings[k + 1], alt_swings[k + 2]
        if p1[1] == "L" and p2[1] == "H" and p3[1] == "L":
            if p3[2] > p1[2] and p2[2] > p1[2]:
                primaries.append({"p1_idx": p1[0], "p1": p1[2], "p2_idx": p2[0], "p2": p2[2], "p3_idx": p3[0], "p3": p3[2]})

    c_arr = close.to_numpy()
    n = len(c_arr)

    setups = []  # each: {'breakout_idx', 'primary'}
    for prim in primaries:
        p2_idx = prim["p2_idx"]
        for i in range(p2_idx, min(p2_idx + hook_lookback, n)):
            if c_arr[i] > prim["p2"]:
                setups.append({"breakout_idx": i, "primary": prim})
                break

    # For each primary breakout, look for a secondary (smaller) hook 1-2-3
    # within hook_lookback bars after the breakout.
    entries = []
    high_arr = high.to_numpy()
    low_arr = low.to_numpy()
    for s in setups:
        b_idx = s["breakout_idx"]
        prim = s["primary"]
        search_end = min(b_idx + hook_lookback, n)
        # secondary swing high after breakout
        hook_top = None
        hook_top_idx = None
        hook_bottom = None
        hook_bottom_idx = None
        for i in range(b_idx + 1, search_end):
            if high_pivots.iloc[i] == 1 and hook_top is None:
                hook_top = high_arr[i]
                hook_top_idx = i
                continue
            if hook_top is not None and low_pivots.iloc[i] == -1 and hook_bottom is None:
                if low_arr[i] > prim["p3"]:
                    hook_bottom = low_arr[i]
                    hook_bottom_idx = i
                continue
            if hook_bottom is not None and c_arr[i] > hook_top:
                entries.append({
                    "entry_idx": i,
                    "hook_top": hook_top,
                    "hook_bottom": hook_bottom,
                    "leg_height": prim["p2"] - prim["p1"],
                })
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
                stop_price = e["hook_bottom"]
                target_price = e["hook_top"] + target_r_multiple * e["leg_height"]
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
