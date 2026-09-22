"""Strategy: Bullish Bat harmonic pattern (XABCD Fibonacci structure).

Hypothesis (see knowledge_base/strategies_log.jsonl for this id):
The Bat harmonic pattern (Scott Carney) is a 4-leg (X-A-B-C-D) reversal
structure defined by specific Fibonacci retracement/extension ratios. Per
https://tradingstrategyguides.com/harmonic-bat-pattern-strategy/ (read via
browser_exec this iteration -- web_search DDGS backend TLS-errored on 2
consecutive queries this trigger, fell back to Google via browser), the
source's own disclosed numeric rules for a valid BULLISH Bat are:
    - AB = 0.382 to 0.50 Fibonacci retracement of the XA leg
    - BC = 0.382 to 0.886 Fibonacci retracement of the AB leg
    - CD = 0.886 Fibonacci retracement of the XA leg (completion point D),
      or equivalently a 1.618-2.618 Fibonacci extension of the AB leg
A completed D point (within tolerance of the 0.886 XA retracement) is a
long entry signal (harmonic reversal); risk management uses a stop below D
and a target back toward the C point (standard harmonic-trading practice
since the source's own strategy write-up recommends "measured move" targets
without giving one universal numeric target).

This repo has 0 prior "Bat pattern" entries (distinct from the repo's
existing Gartley harmonic-pattern entries, which use different Fibonacci
ratios: Gartley's AB retraces exactly 0.618 of XA vs Bat's 0.382-0.50, and
Gartley's D completes at 0.786 of XA vs Bat's 0.886).

Implementation notes
---------------------
Swing points (X, A, B, C, D candidates) are detected via a simple rolling
fractal: a local high/low over a `swing_window`-bar window on each side.
The four most recent alternating swing points are checked against the
Bat's Fibonacci ratio rules (with a `tolerance` band around each ratio,
since real price data rarely hits Fibonacci ratios exactly). When a valid
bullish XABCD sequence completes (i.e. price closes near the D point after
satisfying the AB/BC/CD ratio checks), a long entry triggers; exit at a
fixed R-multiple target/stop or a `max_hold_days` time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _find_swings(high: pd.Series, low: pd.Series, swing_window: int) -> pd.DataFrame:
    """Return a DataFrame of alternating swing highs/lows with their index positions."""
    n = len(high)
    is_swing_high = pd.Series(False, index=high.index)
    is_swing_low = pd.Series(False, index=low.index)
    for i in range(swing_window, n - swing_window):
        window_h = high.iloc[i - swing_window : i + swing_window + 1]
        window_l = low.iloc[i - swing_window : i + swing_window + 1]
        if high.iloc[i] == window_h.max():
            is_swing_high.iloc[i] = True
        if low.iloc[i] == window_l.min():
            is_swing_low.iloc[i] = True
    return is_swing_high, is_swing_low


def _ratio_in_range(actual: float, lo: float, hi: float, tolerance: float) -> bool:
    return (lo - tolerance) <= actual <= (hi + tolerance)


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 5,
    tolerance: float = 0.08,
    max_hold_days: int = 15,
    stop_r_mult: float = 1.0,
    target_r_mult: float = 1.618,
) -> pd.Series:
    """Return a {0,1} long/flat position series based on completed bullish Bat patterns."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]
    n = len(close)

    is_swing_high, is_swing_low = _find_swings(high, low, swing_window)

    swing_points = []  # (idx, price, type) type: 'H' or 'L'
    for i in range(n):
        if is_swing_high.iloc[i]:
            swing_points.append((i, high.iloc[i], "H"))
        elif is_swing_low.iloc[i]:
            swing_points.append((i, low.iloc[i], "L"))
    swing_points.sort(key=lambda t: t[0])

    # Keep only strictly alternating swings (drop consecutive same-type,
    # keeping the more extreme one) for a clean XABCD zig-zag.
    clean = []
    for pt in swing_points:
        if clean and clean[-1][2] == pt[2]:
            if pt[2] == "H" and pt[1] > clean[-1][1]:
                clean[-1] = pt
            elif pt[2] == "L" and pt[1] < clean[-1][1]:
                clean[-1] = pt
        else:
            clean.append(pt)

    position = pd.Series(0, index=close.index, dtype=int)
    entries = []  # (entry_idx, stop_price, target_price)

    # For a bullish Bat: X(low)-A(high)-B(low)-C(high)-D(low), completion at D
    for k in range(4, len(clean)):
        x_pt, a_pt, b_pt, c_pt, d_pt = clean[k - 4], clean[k - 3], clean[k - 2], clean[k - 1], clean[k]
        if not (x_pt[2] == "L" and a_pt[2] == "H" and b_pt[2] == "L" and c_pt[2] == "H" and d_pt[2] == "L"):
            continue
        X, A, B, C, D = x_pt[1], a_pt[1], b_pt[1], c_pt[1], d_pt[1]
        xa = A - X
        ab = A - B
        bc = C - B
        cd = C - D
        if xa <= 0 or ab <= 0 or bc <= 0 or cd <= 0:
            continue
        ab_retrace = ab / xa
        bc_retrace = bc / ab
        cd_retrace_of_xa = cd / xa

        valid_ab = _ratio_in_range(ab_retrace, 0.382, 0.50, tolerance)
        valid_bc = _ratio_in_range(bc_retrace, 0.382, 0.886, tolerance)
        valid_cd = _ratio_in_range(cd_retrace_of_xa, 0.786, 0.886, tolerance)  # widen slightly for tolerance

        if valid_ab and valid_bc and valid_cd:
            entry_idx = d_pt[0]
            if entry_idx + 1 < n:
                stop_price = D - stop_r_mult * (C - D) if C > D else D * 0.97
                risk = D - stop_price if D > stop_price else D * 0.03
                target_price = D + target_r_mult * risk
                entries.append((entry_idx + 1, stop_price, target_price))

    in_position = False
    entry_i = 0
    stop_p = 0.0
    target_p = 0.0
    entries_by_idx = {e[0]: e for e in entries}
    for i in range(n):
        if not in_position and i in entries_by_idx:
            _, stop_p, target_p = entries_by_idx[i]
            in_position = True
            entry_i = i
        if in_position:
            held = i - entry_i
            price = close.iloc[i]
            if price <= stop_p or price >= target_p or held >= max_hold_days:
                position.iloc[i] = 1 if i == entry_i else 0
                if i != entry_i:
                    in_position = False
                else:
                    position.iloc[i] = 1
            else:
                position.iloc[i] = 1
        else:
            position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
