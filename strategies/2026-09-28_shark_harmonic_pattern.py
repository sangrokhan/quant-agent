"""Strategy: Bullish Shark harmonic pattern (0-X-A-B-C, Scott Carney).

Hypothesis (source: https://harmonicsprotrader.com/theoretical-framework/harmonics-theory/shark-pattern/,
read 2026-09-28 via browser_exec):

The Shark is one of the newer harmonic patterns (Scott Carney), labelled
0-X-A-B-C rather than the classic X-A-B-C-D -- a reversal pattern that
completes at a DEEP EXTENSION of the initial leg (over-stretched price),
distinct from Bat/Gartley/Crab/Cypher (all already tested in this repo,
labelled X-A-B-C-D) which complete at retracements or extensions of the
XA leg specifically. Source's disclosed ratio rules:
  Rule 1 (AB leg): AB retraces to a 1.13-1.618 extension of the XA leg.
  Rule 2 (BC leg): completion at C is a deep 1.618-2.24 extension
    (measured from the 0 point via the B-C leg).
  Rule 3 (0-X harmonic ratio): completion at C also aligns with an
    0.886-1.13 relationship to the 0-X leg -- i.e. C extends
    0.886x-1.13x beyond X relative to the 0-X leg's length. This
    confluence with Rule 2 is what the source calls "genuine" vs a
    lookalike.

First "Shark" harmonic pattern in this repo (0 prior hits in
strategies_index.jsonl for "Shark pattern"/"0-X-A-B-C" -- distinct from
the already-tested Bulkowski "Shark-32" CANDLESTICK pattern, which is an
unrelated three-inside-day continuation setup, and from this repo's other
XABCD harmonics (Crab/Cypher/Bat/Gartley) which all use a different point
count/labelling and complete at D rather than C).

Mechanical proxy (daily-bar swing-pivot scaffolding, reused from this
repo's other harmonic strategies -- exact ratio disambiguation between
Rule 2's "0-B" and "B-C" wording is collapsed into a single 0-X-relative
projection per Rule 3, the more concretely stated of the two overlapping
completion rules):
  1. Detect alternating swing pivots via centered rolling-window fractals:
     for a BULLISH Shark, look for O(high)-X(low)-A(high)-B(low)
     quadruple (four alternating swings).
  2. OX = O - X, XA = A - X, AB = A - B.
  3. Rule 1 filter: ab_xa_ratio = AB / XA must be in
     [ab_xa_ext_min, ab_xa_ext_max] (default 1.13-1.618).
  4. Project completion C = B - c_ext * OX, with c_ext (the 0-X
     relationship per Rule 3) in [c_ext_min, c_ext_max] (default
     0.886-1.13). Require C < X (the pattern's defining "extreme,
     beyond X" over-extension property).
  5. Entry: first bar price touches the C-zone (within c_tolerance of the
     projected C level) after B's index.
  6. Exit: close crosses below C*(1-stop_buffer) (stop), or close
     reaches C + target_bc_retrace*(B - C) (partial retracement of the
     BC leg back toward B, i.e. the reciprocal-move idea the source
     mentions), or a max_hold_days time-stop.

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
    """Return a Series of +1 (swing high), -1 (swing low), 0 (none) using a
    centered rolling window fractal test."""
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
    pivot_window: int = 11,
    ab_xa_ext_min: float = 1.13,
    ab_xa_ext_max: float = 1.618,
    c_ext_min: float = 0.886,
    c_ext_max: float = 1.13,
    c_tolerance: float = 0.02,
    target_bc_retrace: float = 0.382,
    stop_buffer: float = 0.015,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series for bullish Shark completions."""
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

    quads = []
    for k in range(len(alt_swings) - 3):
        o, x, a, b = alt_swings[k], alt_swings[k + 1], alt_swings[k + 2], alt_swings[k + 3]
        if o[1] == "H" and x[1] == "L" and a[1] == "H" and b[1] == "L":
            O, X, A, B = o[2], x[2], a[2], b[2]
            OX = O - X
            XA = A - X
            AB = A - B
            if OX <= 0 or XA <= 0 or AB <= 0:
                continue
            ab_xa_ratio = AB / XA
            if not (ab_xa_ext_min <= ab_xa_ratio <= ab_xa_ext_max):
                continue
            if B >= A:
                continue
            c_ext = (c_ext_min + c_ext_max) / 2.0
            c_price = B - c_ext * OX
            if c_price >= X:
                continue  # Shark's defining property: C projects beyond (below) X
            quads.append({"b_idx": b[0], "B": B, "C": c_price})

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = 0.0
    target_price = 0.0
    used = set()

    c_arr = close.values
    n = len(c_arr)

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if c_arr[i] < stop_price or c_arr[i] >= target_price or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            for q_idx, q in enumerate(quads):
                if q_idx in used:
                    continue
                if i <= q["b_idx"]:
                    continue
                c_price = q["C"]
                if abs(c_arr[i] - c_price) <= c_tolerance * abs(c_price):
                    in_position = True
                    entry_idx = i
                    stop_price = c_price * (1 - stop_buffer)
                    target_price = c_price + target_bc_retrace * (q["B"] - c_price)
                    used.add(q_idx)
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
