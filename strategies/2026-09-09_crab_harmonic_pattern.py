"""Strategy: Bullish Crab harmonic pattern (XABCD, Scott Carney).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Google's AI-overview synthesis of naga.com/LiteFinance/Investopedia's
"Crab harmonic pattern" pages (query: "Crab harmonic pattern fibonacci
ratios specific trading rules"), the Crab (attributed to Scott Carney) is
the most extreme of the classic harmonic XABCD patterns: AB retraces
38.2%-61.8% of XA (B never exceeds A), BC retraces 38.2%-88.6% of AB, and
the CD leg extends 2.24x-3.618x the BC leg, which the source states
equals approximately a 1.618x extension of the ORIGINAL XA leg -- i.e.
point D projects well BEYOND point X (the pattern's defining "extreme"
characteristic, unlike Bat's 0.886 retracement of XA which stays inside
the XA range, or Gartley's 0.786). Entry at D inside the PRZ on reversal
confirmation; stop just beyond the extreme completion limit; profit
targets scaled out at C, B, A, X retracement levels (this repo
simplifies to a single target at a retracement of the CD leg per the
already-tested AB=CD/Bat sibling strategies for a controlled comparison).

Distinct construction from all three harmonic patterns already tested in
this repo (AB=CD accepted, Gartley rejected, Bat rejected): the Crab's D
projection uses XA extension (1.618x XA beyond A, i.e. below X for a
bullish Crab) rather than an XA retracement, making it mechanically the
"opposite direction" completion relative to Bat/Gartley.

Signal logic (bullish Crab only, long-only), reusing the same
rolling-fractal swing-pivot scaffolding as the sibling harmonic strategies:
    1. Detect alternating swing highs/lows via a centered rolling window.
    2. For each valid X(low)-A(high)-B(low)-C(high) quadruple:
         XA = A - X
         AB = A - B, ab_retrace = AB/XA, valid in [0.382, 0.618]
         C must not exceed A
         BC = C - B, bc_retrace = BC/AB, valid in [0.382, 0.886]
    3. Project D via the XA-extension formulation: D_price = A -
       xa_extension * XA (xa_extension around 1.618, i.e. D projects BELOW
       X for a bullish reversal). Require D_price < X (the "extreme,
       beyond X" defining property).
    4. Entry: first bar price touches the D-zone (within d_tolerance of
       D_price) after C's index.
    5. Exit: close crosses below D_price*(1-stop_buffer) (stop), or close
       reaches D_price + target_cd_retrace*(C - D_price) (retracement of
       the CD leg back toward C), or a max_hold_days time-stop.
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
    ab_min: float = 0.382,
    ab_max: float = 0.618,
    bc_min: float = 0.382,
    bc_max: float = 0.886,
    xa_extension: float = 1.618,
    d_tolerance: float = 0.02,
    target_cd_retrace: float = 0.382,
    stop_buffer: float = 0.015,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series for bullish Crab completions."""
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
        x, a, b, c = alt_swings[k], alt_swings[k + 1], alt_swings[k + 2], alt_swings[k + 3]
        if x[1] == "L" and a[1] == "H" and b[1] == "L" and c[1] == "H":
            X, A, B, C = x[2], a[2], b[2], c[2]
            XA = A - X
            AB = A - B
            if XA <= 0 or AB <= 0:
                continue
            ab_retrace = AB / XA
            if not (ab_min <= ab_retrace <= ab_max):
                continue
            if C >= A:
                continue
            BC = C - B
            if BC <= 0:
                continue
            bc_retrace = BC / AB
            if not (bc_min <= bc_retrace <= bc_max):
                continue
            d_price = A - xa_extension * XA
            if d_price >= X:
                continue  # Crab's defining property: D projects beyond (below) X
            quads.append({"c_idx": c[0], "C": C, "D": d_price})

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
                if i <= q["c_idx"]:
                    continue
                d_price = q["D"]
                if abs(c_arr[i] - d_price) <= d_tolerance * d_price:
                    in_position = True
                    entry_idx = i
                    stop_price = d_price * (1 - stop_buffer)
                    target_price = d_price + target_cd_retrace * (q["C"] - d_price)
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
