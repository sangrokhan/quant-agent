"""Strategy: Bulkowski "Busted Pattern" failed-breakdown reversal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-020):
Per Thomas Bulkowski's chart-pattern research (thepatternsite.com, "busted
pattern" concept applied across dozens of his pattern-pair studies, e.g.
https://www.thepatternsite.com/ppDescScallops.html, visited this
iteration): a "busted" bearish breakdown occurs when price breaks below a
support level, drops NO MORE than a bounded percentage (Bulkowski's
studies consistently use a 10% cap across pattern types) before reversing,
and then closes back ABOVE the original support level -- a failed
breakdown whose failure itself becomes the buy signal (per Bulkowski's own
finding across multiple pattern studies that busted patterns often
outperform their non-busted counterparts).

This repo operationalizes the GENERIC busted-pattern mechanic (not tied to
any single specific chart-pattern shape like scallops/triangles/rectangles,
which Bulkowski's site catalogs dozens of variants of) using a rolling
N-day price low as the generic "support" reference level: (1) support =
rolling min close over `lookback` bars PRIOR to any breakdown, (2)
breakdown = close crosses below support, (3) the breakdown is "busted" if,
within `bust_window` bars of the breakdown, the lowest close reached is no
more than `max_drop_pct` below the support level (bounded failure, per
Bulkowski's ~10% convention) AND close subsequently recovers back above
support, (4) entry on that recovery-above-support bar.

Distinct from this repo's existing Swing Failure Pattern entry
(`2026-09-09-087`, rejected -- SAME-BAR wick-below-then-close-above
rejection, a single-candle mechanic) because this is a MULTI-DAY
breakdown-and-recovery mechanic with an explicit magnitude cap on how far
price is allowed to have dropped before the reversal still counts as
"busted" (Bulkowski's defining characteristic), not a single-bar wick
rejection.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 20,
    bust_window: int = 10,
    max_drop_pct: float = 0.10,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    # Support level: rolling min of close over `lookback` bars, computed
    # BEFORE the current bar (shifted) so it represents a pre-existing
    # reference level, not one contaminated by the breakdown bar itself.
    support = close.shift(1).rolling(lookback).min()

    breakdown = close < support

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    # Track breakdown state: once a breakdown starts, watch for either a
    # "bust" (recovery above support within bust_window bars, without
    # dropping more than max_drop_pct below support) or expiry.
    breakdown_active = False
    breakdown_start_idx = -1
    breakdown_support_level = None
    min_close_since_breakdown = None

    for i in range(len(close)):
        price = close.iloc[i]

        if in_position:
            held = i - entry_idx
            if held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
            continue

        if breakdown_active:
            elapsed = i - breakdown_start_idx
            min_close_since_breakdown = min(min_close_since_breakdown, price)
            drop_pct = (breakdown_support_level - min_close_since_breakdown) / breakdown_support_level

            if price > breakdown_support_level and drop_pct <= max_drop_pct:
                # Busted! Reversal confirmed within the drop-magnitude cap.
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
                breakdown_active = False
                continue
            elif elapsed >= bust_window or drop_pct > max_drop_pct:
                # Breakdown expired or dropped too far -- not a bust, reset.
                breakdown_active = False

        if not breakdown_active and not in_position:
            if bool(breakdown.iloc[i]) if pd.notna(breakdown.iloc[i]) else False:
                breakdown_active = True
                breakdown_start_idx = i
                breakdown_support_level = support.iloc[i]
                min_close_since_breakdown = price
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
