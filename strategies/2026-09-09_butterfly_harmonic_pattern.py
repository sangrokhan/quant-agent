"""Strategy: Bullish Butterfly harmonic pattern (XABCD 5-point structure).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-029):
Per dhan.co's "Harmonic Butterfly Pattern" explainer
(https://dhan.co/blog/technical-analysis/harmonic-butterfly-pattern/), the
Butterfly is a 5-point XABCD zigzag pattern with Fibonacci ratios distinct
from both the Gartley (already tested/rejected, 2026-09-08-108) and the Bat
(already tested/rejected, 2026-09-09-017) patterns already in this repo:
    - Point B retraces ~78.6% of leg XA (a much deeper retracement than the
      Bat's 38.2-50% or the Gartley's ~61.8%).
    - Point C retraces 38.2%-88.6% of leg AB.
    - Point D (the "Potential Reversal Zone", PRZ) is the pattern's defining
      distinguishing feature: it extends 161.8%-261.8% of leg BC AND
      approximately 127.2% BEYOND point X (i.e. D overshoots the pattern's
      starting point X, unlike Gartley/Bat/AB=CD which all complete D
      *inside* the XA range). This overextension is the source's own
      explanation for why the Butterfly signals trend exhaustion after a
      blow-off move past the prior extreme.

Entry is taken inside the PRZ (near the D projection, which lies BEYOND X)
on a reversal confirmation touch; stop placed just beyond the pattern
extreme (a further small buffer past D); target set at a partial
retracement of the CD leg back toward C, mirroring this repo's existing
AB=CD/Bat/Gartley harmonic-pattern strategy shape (reusing the same rolling
`pivot_window`-bar fractal swing-detection scaffolding as
strategies/2026-09-08_abcd_harmonic_pattern.py and
strategies/2026-09-09_bat_harmonic_pattern.py).

Signal logic (bullish Butterfly only, long-only):
    1. Detect alternating swing highs/lows via a centered rolling window.
    2. For each valid X(low)-A(high)-B(low)-C(high) quadruple (bullish
       Butterfly bottoms out at D, so X, B, D are lows and A, C are highs):
         XA = A - X
         AB = A - B  (retrace of XA)
         ab_retrace = AB / XA, valid if in [ab_min, ab_max] (~0.786 band)
         BC = C - B
         bc_retrace = BC / AB, valid if in [bc_min, bc_max], C must not
             exceed A (bc top must stay below A)
    3. Project D via the XA-extension formulation (D overshoots X):
         D_price = X - xa_extension_beyond_x * XA   (xa_extension_beyond_x
             around 0.272, i.e. the ~127.2% total XA extension measured
             from A, equivalently ~27.2% of XA further below X)
         require D_price < X (a genuine overshoot, the pattern's defining
             trait) -- this is what makes the Butterfly distinct from the
             already-tested Bat (D stays above X) and Gartley (D at 78.6%
             retracement, inside XA).
    4. Entry: first bar price touches the D-zone (within d_tolerance of
       D_price) after C's index.
    5. Exit: close crosses below D_price*(1-stop_buffer) (stop), or close
       reaches D_price + target_cd_retrace*(C - D_price) (partial
       retracement of the CD leg back toward C), or a max_hold_days
       time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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
    ab_min: float = 0.70,
    ab_max: float = 0.886,
    bc_min: float = 0.382,
    bc_max: float = 0.886,
    xa_extension_beyond_x: float = 0.272,
    d_tolerance: float = 0.02,
    target_cd_retrace: float = 0.382,
    stop_buffer: float = 0.015,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series for bullish Butterfly completions."""
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

    # Build candidate X(L)-A(H)-B(L)-C(H) quadruples (bullish Butterfly
    # bottoms at D, which lies BELOW X).
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
                continue  # C must not exceed A
            BC = C - B
            if BC <= 0:
                continue
            bc_retrace = BC / AB
            if not (bc_min <= bc_retrace <= bc_max):
                continue
            d_price = X - xa_extension_beyond_x * XA
            if d_price >= X:
                continue  # D must overshoot X (the Butterfly's defining trait)
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
