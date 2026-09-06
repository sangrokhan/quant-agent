"""Strategy: Andrews Pitchfork median-line mean-reversion (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl):
Andrews' Pitchfork (Alan Andrews) anchors a "median line" and two parallel
"tine" lines through three alternating swing pivots (A, then B, then C):
the median line runs from A through the midpoint of B and C, with the tines
parallel to it through B and C respectively. Per LiteFinance's mean-reversion
interpretation: "Exit the position at the median line or the opposite
boundary of the channel" -- i.e. price reacting off a tine (the fork's outer
boundary) and reverting toward the median line (the fork's "center of
gravity", per LuxAlgo's description) is the tradeable mean-reversion setup.
We operationalize the bullish case (Low-High-Low pivot triple, ascending
fork): detect the three most recent alternating swing pivots using a
`swing_length`-bar fractal window; construct the median line (through A and
midpoint of B,C) and the lower tine (parallel, through C, the most recent
Low pivot); long entry when price touches/dips to within `tine_tolerance`
of the lower tine and closes back above it (a bounce off the tine); exit
when price reaches the median line, the fork's pivots go stale
(`max_pivot_age` bars since C with no new pivot), or a max_hold_days
time-stop.

Source: https://www.luxalgo.com/library/indicator/andrews-pitchfork/
(construction: "three most recent confirmed alternating swing pivots become
A, B and C... a thicker median line from the handle through the B-C
midpoint, parallel tines through B and C") and
https://www.litefinance.org (mean-reversion trading rule: "Exit the position
at the median line or the opposite boundary of the channel").

First Andrews-Pitchfork strategy in this repo -- distinct from other
swing-pivot/channel constructions already tested (Fibonacci retracement
pullback -- a fixed retracement-fraction zone, not a forward-projected
parallel-line channel; Regression Channel -- OLS-fit not pivot-anchored;
Donchian/Keltner -- fixed-width rolling channels, not sloped/pivot-anchored)
since the pitchfork's median+tine lines are SLOPED lines anchored to
specific historical pivot points and projected forward in time.

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


def _find_pivots(close: pd.Series, swing_length: int) -> list[tuple[int, float, str]]:
    """Return a list of (index_position, price, 'H'|'L') for confirmed
    fractal swing pivots: a bar is a pivot high/low if it is the
    max/min over the window [-swing_length, +swing_length] around it."""
    c = close.to_numpy(dtype=float)
    n = len(c)
    pivots = []
    for i in range(swing_length, n - swing_length):
        window = c[i - swing_length : i + swing_length + 1]
        if c[i] == window.max() and c[i] != c[i - 1]:
            pivots.append((i, c[i], "H"))
        elif c[i] == window.min() and c[i] != c[i - 1]:
            pivots.append((i, c[i], "L"))
    return pivots


def _alternating_triples(pivots: list[tuple[int, float, str]]) -> list[tuple]:
    """Filter consecutive pivots to strictly alternate H/L, keeping only
    the most extreme pivot when two of the same type occur back-to-back,
    then return the list of alternating (idx, price, type) pivots."""
    alt = []
    for p in pivots:
        if not alt:
            alt.append(p)
            continue
        if p[2] == alt[-1][2]:
            # same type as last -- keep the more extreme one
            if (p[2] == "H" and p[1] > alt[-1][1]) or (p[2] == "L" and p[1] < alt[-1][1]):
                alt[-1] = p
        else:
            alt.append(p)
    return alt


def generate_signals(
    price_df: pd.DataFrame,
    swing_length: int = 10,
    tine_tolerance: float = 0.01,
    max_pivot_age: int = 60,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)
    c = close.to_numpy(dtype=float)

    pivots = _find_pivots(close, swing_length)
    alt_pivots = _alternating_triples(pivots)

    # Build a per-bar "active fork" lookup: for each bar t, the most recent
    # completed bullish (Low-High-Low) triple (A,B,C) known as of bar t
    # (pivots are only "confirmed" swing_length bars after they occur).
    fork_at = [None] * n  # each entry: (a_idx,a_px,b_idx,b_px,c_idx,c_px)
    current_fork = None
    triple_ptr = 0
    # Precompute confirmed-bullish-triples as they become available (in
    # order of the confirming pivot C, confirmed at c_idx+swing_length)
    bullish_triples = []
    for i in range(len(alt_pivots) - 2):
        a, b, cpv = alt_pivots[i], alt_pivots[i + 1], alt_pivots[i + 2]
        if a[2] == "L" and b[2] == "H" and cpv[2] == "L":
            confirm_bar = cpv[0] + swing_length
            bullish_triples.append((confirm_bar, a, b, cpv))

    bt_ptr = 0
    for t in range(n):
        while bt_ptr < len(bullish_triples) and bullish_triples[bt_ptr][0] <= t:
            _, a, b, cpv = bullish_triples[bt_ptr]
            current_fork = (a[0], a[1], b[0], b[1], cpv[0], cpv[1])
            bt_ptr += 1
        fork_at[t] = current_fork

    long_trigger = np.zeros(n, dtype=bool)
    exit_trigger = np.zeros(n, dtype=bool)
    fork_stale = np.zeros(n, dtype=bool)

    for t in range(n):
        fork = fork_at[t]
        if fork is None:
            continue
        a_idx, a_px, b_idx, b_px, c_idx, c_px = fork
        if t - c_idx > max_pivot_age:
            fork_stale[t] = True
            continue
        if c_idx == a_idx:
            continue
        slope = ((b_px + c_px) / 2.0 - a_px) / (c_idx - a_idx)
        median_at_t = a_px + slope * (t - a_idx)
        tine_at_t = median_at_t + (c_px - (a_px + slope * (c_idx - a_idx)))
        # tine (through C) value at bar t
        if tine_at_t == 0:
            continue
        near_tine = abs(c[t] - tine_at_t) / abs(tine_at_t) <= tine_tolerance
        bounced_above = c[t] > tine_at_t
        if near_tine and bounced_above and c[t - 1] <= tine_at_t if t > 0 else False:
            long_trigger[t] = True
        if c[t] >= median_at_t:
            exit_trigger[t] = True

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_trigger[i]) or bool(fork_stale[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(long_trigger[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1

    position.name = "position"
    return position


def generate_returns(
    price_df: pd.DataFrame,
    swing_length: int = 10,
    tine_tolerance: float = 0.01,
    max_pivot_age: int = 60,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        swing_length=swing_length,
        tine_tolerance=tine_tolerance,
        max_pivot_age=max_pivot_age,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns.name = "strategy_returns"
    return strat_returns
