"""Strategy: Cypher Harmonic Pattern (bullish) — X-A-B-C-D Fibonacci reversal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-036):
Per multiple corroborating sources (TradingView's Cypher-pattern
documentation and arongroups.co's "Cypher Pattern Guide: Rules, Ratios &
Strategy", both surfaced via a Google AI-overview synthesis after
`web_search` returned no results for this specific query -- `browser_exec`
fallback used per RESEARCH_LOOP.md Step 2): the Cypher harmonic pattern is
a 5-point (X, A, B, C, D) / 4-leg (XA, AB, BC, CD) reversal pattern defined
by precise Fibonacci ratio rules:
  - Point B retraces the XA leg between 38.2% and 61.8% (invalid if it
    exceeds 61.8%).
  - Point C extends beyond point A, landing at 113%-141.4% of the XA leg
    length (measured from point A).
  - Point D (the Potential Reversal Zone, PRZ) sits at the 78.6%
    retracement of the XC leg.
  - Entry is taken at point D completion; stop-loss below point X (long
    case); target 1 at point A, target 2 at point C.

This is the first harmonic pattern with this specific X-A-B-C-D
ratio-chain construction in this repo (0 prior "Cypher" hits; distinct
from the repo's existing Gartley/Bat/Butterfly harmonic-pattern entries,
each of which uses different specific Fibonacci ratio bands for B/C/D).
Swing points (X, A, B, C) are detected programmatically as local
extrema (fractal pivots) over a rolling `swing_window`; a valid bullish
Cypher requires X=low, A=high, B=low, C=high in alternating order with the
ratio checks above; D is the DERIVED PRZ level (not an observed swing
point) -- entry triggers when price first touches/crosses down into the D
level after C is confirmed, with a stop below X and profit target at A
(the source's own first target).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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


def _find_swing_points(high: pd.Series, low: pd.Series, swing_window: int):
    """Fractal pivot detection: a swing high at i if high[i] is the max of
    the window [i-swing_window, i+swing_window]; a swing low analogously.
    Returns two boolean Series (swing_high, swing_low)."""
    roll_max = high.rolling(2 * swing_window + 1, center=True).max()
    roll_min = low.rolling(2 * swing_window + 1, center=True).min()
    swing_high = (high == roll_max) & high.notna()
    swing_low = (low == roll_min) & low.notna()
    return swing_high.fillna(False), swing_low.fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 5,
    b_retrace_min: float = 0.382,
    b_retrace_max: float = 0.618,
    c_ext_min: float = 1.13,
    c_ext_max: float = 1.414,
    d_retrace: float = 0.786,
    d_tolerance: float = 0.03,
    max_hold_days: int = 30,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a {0, leverage_cap} long/flat position series.

    Detects bullish Cypher (X=low, A=high, B=low, C=high) patterns from
    swing pivots; enters long when price reaches the derived D (PRZ) level
    within d_tolerance after a valid C is confirmed; exits at point A
    (take-profit), a stop below X, or a max_hold_days time-stop.
    """
    df = _prep(price_df)
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]
    n = len(close)

    swing_high, swing_low = _find_swing_points(high, low, swing_window)

    # Collect ordered swing pivots (index position, type, price)
    pivots = []
    for i in range(n):
        if swing_low.iloc[i]:
            pivots.append((i, "low", low.iloc[i]))
        elif swing_high.iloc[i]:
            pivots.append((i, "high", high.iloc[i]))
    # Deduplicate consecutive same-type pivots (keep the more extreme one)
    cleaned = []
    for p in pivots:
        if cleaned and cleaned[-1][1] == p[1]:
            if (p[1] == "low" and p[2] < cleaned[-1][2]) or (p[1] == "high" and p[2] > cleaned[-1][2]):
                cleaned[-1] = p
        else:
            cleaned.append(p)

    position = pd.Series(0.0, index=close.index, dtype=float)
    in_position = False
    entry_idx = 0
    entry_x_price = None
    entry_a_price = None

    # For each candidate window of 4 alternating pivots X(low)-A(high)-B(low)-C(high),
    # validate ratios and, if valid, scan forward from C for a D-level touch.
    active_patterns = []  # list of dicts: {c_idx, x, a, b, c, d_level}
    for k in range(len(cleaned) - 3):
        x_i, x_t, x_p = cleaned[k]
        a_i, a_t, a_p = cleaned[k + 1]
        b_i, b_t, b_p = cleaned[k + 2]
        c_i, c_t, c_p = cleaned[k + 3]
        if not (x_t == "low" and a_t == "high" and b_t == "low" and c_t == "high"):
            continue
        xa = a_p - x_p
        if xa <= 0:
            continue
        b_retrace = (a_p - b_p) / xa
        if not (b_retrace_min <= b_retrace <= b_retrace_max):
            continue
        c_ext = (c_p - a_p) / xa + 1.0  # C measured relative to XA length, extension beyond A
        # simpler: C extension of XA leg = (c_p - x_p) / xa (source: "113%-141.4% extension of XA leg")
        c_ext_of_xa = (c_p - x_p) / xa
        if not (c_ext_min <= c_ext_of_xa <= c_ext_max):
            continue
        xc = c_p - x_p
        if xc <= 0:
            continue
        d_level = c_p - d_retrace * xc  # 78.6% retracement of XC leg, down from C
        active_patterns.append({"c_idx": c_i, "x": x_p, "a": a_p, "d_level": d_level})

    # Build a per-bar lookup: for each bar, is there an active pattern (C confirmed, D not yet hit)?
    pattern_by_end_search = {}
    for pat in active_patterns:
        pattern_by_end_search.setdefault(pat["c_idx"], []).append(pat)

    pending = []  # patterns waiting for D touch
    for i in range(n):
        if i in pattern_by_end_search:
            pending.extend(pattern_by_end_search[i])

        if in_position:
            held = i - entry_idx
            hit_target = close.iloc[i] >= entry_a_price
            hit_stop = close.iloc[i] <= entry_x_price
            if hit_target or hit_stop or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0.0
                continue
            position.iloc[i] = leverage_cap
        else:
            # Check pending patterns for a D-level touch on this bar
            triggered = None
            still_pending = []
            for pat in pending:
                d_level = pat["d_level"]
                tol = d_tolerance * d_level if d_level != 0 else 0
                if low.iloc[i] <= d_level + tol:
                    triggered = pat
                    continue  # consume it (don't keep in pending)
                still_pending.append(pat)
            pending = still_pending
            if triggered is not None:
                in_position = True
                entry_idx = i
                entry_x_price = triggered["x"]
                entry_a_price = triggered["a"]
                position.iloc[i] = leverage_cap
            else:
                position.iloc[i] = 0.0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
