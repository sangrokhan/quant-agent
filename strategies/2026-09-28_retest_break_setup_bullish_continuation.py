"""Strategy: Retest & Break Setup bullish breakout-pullback-continuation.

Hypothesis (source: https://www.luxalgo.com/library/indicator/retest-break-setup/,
read 2026-09-28 via browser_exec while browsing LuxAlgo's indicator library
for a fresh angle -- 0 prior hits confirmed via strategies_index.jsonl
before implementation):

LuxAlgo's "Retest & Break Setup" detects the full breakout-pullback-
continuation sequence: a pivot HIGH breaks (bullish case), price returns
to PROBE (retest) the broken level -- which now must hold as SUPPORT
through `required_retests` consecutive touches within `max_bars_between_
retests` of each other -- and a close beyond the retest phase's own
highest high (not just back above the original pivot) completes/confirms
the continuation. Source's own framing: "Retests that hold concentrate
stops and breakout orders around the extremes, so a confirmed break can
tap that liquidity for a stronger continuation."

This is a genuinely more disciplined breakout construction than a naive
single-bar pivot break: it specifically requires the broken level to be
RE-TESTED AND HOLD (not just crossed once) before confirming, filtering
out breakouts that immediately fail back through the level. First
"Retest & Break Setup" strategy in this repo (distinct from this repo's
many single-stage breakout strategies, and from Wyckoff Markup's
different range-height/volume-expansion-based confirmation tested
earlier this same cron trigger).

Signal logic
------------
- Pivot high: a local high over a `pivot_length`-bar window on each side
  (standard swing-pivot detection: high[t] is the max of high[t-pivot_
  length : t+pivot_length+1]). Confirmed with `pivot_length`-bar lag
  (no lookahead).
- Break: close crosses above a confirmed, not-yet-broken pivot high.
- Retest phase: after the break, count consecutive bars where price
  returns to within `retest_proximity_pct`% of the broken pivot level
  (touches it) without closing back below it -- each such touch (spaced
  no more than `max_bars_between_retests` apart) counts toward
  `required_retests`. If price closes back below the pivot level before
  accumulating enough retests, the setup invalidates.
- Confirmation/entry: once `required_retests` valid retests have
  occurred (within `max_bars_for_break` bars of the original break),
  a close above the HIGHEST HIGH reached during the retest phase
  completes the setup -> long entry at that close.
- Exit: close falls back below the broken pivot level (support given
  up, setup invalidated post-entry), or a max_hold_days time-stop.

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


def _confirmed_pivot_highs(high: np.ndarray, pivot_length: int) -> np.ndarray:
    n = len(high)
    is_pivot = np.zeros(n, dtype=bool)
    for i in range(pivot_length, n - pivot_length):
        window = high[i - pivot_length : i + pivot_length + 1]
        if high[i] == window.max():
            is_pivot[i] = True
    return is_pivot


def _compute_trades(
    df: pd.DataFrame,
    pivot_length: int,
    required_retests: int,
    max_bars_between_retests: int,
    max_bars_for_break: int,
    retest_proximity_pct: float,
    max_hold_days: int,
):
    close = df["close"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    n = len(df)

    is_pivot = _confirmed_pivot_highs(high, pivot_length)

    trades = []
    i = 0
    # Track confirmed pivot levels not yet broken.
    active_pivots = []  # list of (pivot_idx, pivot_level)
    confirm_lag = pivot_length  # a pivot at idx p is only knowable at p+confirm_lag

    while i < n:
        # Register newly-confirmed pivots.
        confirm_idx = i - confirm_lag
        if 0 <= confirm_idx < n and is_pivot[confirm_idx]:
            active_pivots.append((confirm_idx, high[confirm_idx]))

        # Check for a break of any active pivot at bar i.
        broke = None
        for p_idx, p_level in list(active_pivots):
            if close[i] > p_level:
                broke = (p_idx, p_level)
                active_pivots.remove((p_idx, p_level))
                # Also drop any pivot levels below this one (already broken).
                active_pivots = [(pi, pl) for pi, pl in active_pivots if pl > p_level]
                break

        if broke is not None:
            _, pivot_level = broke
            break_idx = i
            retest_count = 0
            last_touch_idx = break_idx
            retest_high = high[break_idx]
            invalidated = False
            confirmed_entry_idx = None

            for k in range(break_idx + 1, min(break_idx + 1 + max_bars_for_break, n)):
                if close[k] < pivot_level:
                    invalidated = True
                    break
                proximity = abs(low[k] - pivot_level) / max(pivot_level, 1e-9)
                touched = proximity <= (retest_proximity_pct / 100.0)
                if touched and (k - last_touch_idx) <= max_bars_between_retests:
                    retest_count += 1
                    last_touch_idx = k

                if retest_count >= required_retests and close[k] > retest_high:
                    confirmed_entry_idx = k
                    break

                retest_high = max(retest_high, high[k])

            if not invalidated and confirmed_entry_idx is not None:
                entry_idx = confirmed_entry_idx
                entry_price = close[entry_idx]
                exit_idx = None
                for m in range(entry_idx + 1, min(entry_idx + 1 + max_hold_days, n)):
                    if close[m] < pivot_level:
                        exit_idx = m
                        break
                if exit_idx is None:
                    exit_idx = min(entry_idx + max_hold_days, n - 1)
                exit_price = close[exit_idx]
                trades.append((entry_idx, exit_idx, entry_price, exit_price))
                i = exit_idx + 1
                continue

        i += 1

    return trades


def generate_signals(
    price_df: pd.DataFrame,
    pivot_length: int = 5,
    required_retests: int = 1,
    max_bars_between_retests: int = 10,
    max_bars_for_break: int = 20,
    retest_proximity_pct: float = 1.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    trades = _compute_trades(
        df, pivot_length, required_retests, max_bars_between_retests,
        max_bars_for_break, retest_proximity_pct, max_hold_days,
    )
    pos = pd.Series(0.0, index=df.index)
    for entry_idx, exit_idx, _, _ in trades:
        pos.iloc[entry_idx : exit_idx + 1] = 1.0
    return pos


def generate_returns(
    price_df: pd.DataFrame,
    pivot_length: int = 5,
    required_retests: int = 1,
    max_bars_between_retests: int = 10,
    max_bars_for_break: int = 20,
    retest_proximity_pct: float = 1.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    trades = _compute_trades(
        df, pivot_length, required_retests, max_bars_between_retests,
        max_bars_for_break, retest_proximity_pct, max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = pd.Series(0.0, index=df.index)

    for entry_idx, exit_idx, entry_price, exit_price in trades:
        if exit_idx > entry_idx:
            strat_ret.iloc[entry_idx + 1 : exit_idx + 1] = daily_ret.iloc[
                entry_idx + 1 : exit_idx + 1
            ]
        exit_close = df["close"].iloc[exit_idx]
        if exit_close != 0 and exit_price != exit_close:
            prior_close = df["close"].iloc[exit_idx - 1] if exit_idx > 0 else df["close"].iloc[exit_idx]
            if prior_close != 0:
                strat_ret.iloc[exit_idx] = (exit_price / prior_close) - 1.0

    return strat_ret
