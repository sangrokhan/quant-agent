"""Strategy: AB=CD harmonic pattern -- bullish completion at point D.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-1xx):
Per SERP-sourced AB=CD harmonic pattern rules (onetradejournal.com snippet
via Google, and corroborated by EBC Financial Group's harmonic-patterns
glossary): the AB=CD pattern is a 4-point zigzag (A-B-C-D) where the BC leg
retraces ~0.618 of the AB leg, and the CD leg extends 1.272-1.618x the BC
leg (approximately reproducing the AB leg's price distance, i.e. CD ~= AB
within a tolerance). Point D marks a high-probability reversal zone; entry
is taken at/just past D on confirmation, stop placed just beyond D (outside
the pattern), target set at a retracement of the CD leg. This is distinct
from the plain Fibonacci-retracement-pullback strategy already tested
(2026-09-03-022, a single-leg retracement with no CD-leg symmetry
requirement) and from Andrews Pitchfork (sloped channel, not zigzag-leg
symmetry) -- first AB=CD/harmonic-leg-symmetry strategy in this repo.

Signal logic (bullish AB=CD only, long-only)
---------------------------------------------
- Identify swing pivots via a rolling `pivot_window`-bar fractal
  (local max/min over a centered window) to get an alternating sequence of
  swing highs/lows: candidates for A (swing low), B (swing high), C (swing
  low), D (in-progress).
- For each valid A(low)-B(high)-C(low) triple where C > A (higher low,
  i.e. BC retraced but didn't make a new low):
    AB = B - A
    BC = B - C
    bc_retrace = BC / AB
    valid if bc_retrace is within [bc_min, bc_max] (default 0.5-0.786,
    centered on the source's 0.618)
  Then project point D: D_price = C + cd_extension * BC, using
  cd_extension in [1.272, 1.618] (default midpoint-driven via param
  cd_extension_target).
- Entry (long): first bar where price *touches* the projected D_price
  zone (within d_tolerance of D_price) after C, and the entry is only
  taken once per completed ABC triple (avoid re-entering the same swing).
- Exit: close crosses back below D_price * (1 - stop_buffer) (stop beyond
  D), OR close reaches D_price + target_cd_retrace * (C - D_price)  --
  a retracement of the CD leg back toward C as the profit target, OR a
  max_hold_days time-stop.
- Flat otherwise.
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
        window_vals = vals[i - half : i + half + 1]
        if vals[i] == window_vals.max() and (window_vals == vals[i]).sum() == 1:
            pivots.iloc[i] = 1
        elif vals[i] == window_vals.min() and (window_vals == vals[i]).sum() == 1:
            pivots.iloc[i] = -1
    return pivots


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 11,
    bc_min: float = 0.5,
    bc_max: float = 0.786,
    cd_extension_target: float = 1.35,
    d_tolerance: float = 0.02,
    target_cd_retrace: float = 0.618,
    stop_buffer: float = 0.01,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series for bullish AB=CD completions."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    high_pivots = _find_pivots(high, pivot_window)
    low_pivots = _find_pivots(low, pivot_window)

    swing_idx = []  # list of (i, type, price) type: 'H' or 'L'
    for i in range(len(df)):
        if high_pivots.iloc[i] == 1:
            swing_idx.append((i, "H", float(high.iloc[i])))
        if low_pivots.iloc[i] == -1:
            swing_idx.append((i, "L", float(low.iloc[i])))
    swing_idx.sort(key=lambda x: x[0])

    # Keep only alternating swings (dedupe consecutive same-type by keeping the more extreme one)
    alt_swings = []
    for s in swing_idx:
        if alt_swings and alt_swings[-1][1] == s[1]:
            if s[1] == "H" and s[2] > alt_swings[-1][2]:
                alt_swings[-1] = s
            elif s[1] == "L" and s[2] < alt_swings[-1][2]:
                alt_swings[-1] = s
        else:
            alt_swings.append(s)

    # Build candidate A(L)-B(H)-C(L) triples
    triples = []
    for k in range(len(alt_swings) - 2):
        a, b, c = alt_swings[k], alt_swings[k + 1], alt_swings[k + 2]
        if a[1] == "L" and b[1] == "H" and c[1] == "L" and c[2] > a[2]:
            A, B, C = a[2], b[2], c[2]
            AB = B - A
            BC = B - C
            if AB <= 0 or BC <= 0:
                continue
            bc_retrace = BC / AB
            if bc_min <= bc_retrace <= bc_max:
                d_price = C + cd_extension_target * BC
                triples.append({"c_idx": c[0], "C": C, "D": d_price})

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = 0.0
    target_price = 0.0
    used_triples = set()

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
            # check if any triple's D-zone is touched at bar i (only after C's index)
            for t_idx, t in enumerate(triples):
                if t_idx in used_triples:
                    continue
                if i <= t["c_idx"]:
                    continue
                d_price = t["D"]
                if abs(c_arr[i] - d_price) <= d_tolerance * d_price:
                    in_position = True
                    entry_idx = i
                    stop_price = d_price * (1 - stop_buffer)
                    # target moves back toward C from D (retracement of the CD leg)
                    target_price = d_price + target_cd_retrace * (t["C"] - d_price)
                    used_triples.add(t_idx)
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
