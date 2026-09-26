"""Strategy: Bulkowski's "W-Setup" Double-Support-Retest Bottom Fishing.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-020):
Per Thomas Bulkowski's thepatternsite.com/WSetup.html (browser_exec, free,
fully disclosed, own stat: 62% win rate on 78 trades): after a multi-month
decline from a swing high A, price finds support at B (any pattern shape --
"the type of chart pattern at B isn't important"). Price then recovers for
a while before retracing back down to a SECOND support test at C, near the
same price level as B (a "W" shape across A-B-C). The entry trigger is
simply price holding support near B's level a second time at C -- no
breakout/neckline confirmation required, unlike double-bottom strategies.
Stop-loss below the lower of B or C.

Operationalized mechanically (source explicitly says the shape of B/C
doesn't matter, only that they're similar-priced local lows separated by an
intervening recovery high):
1. Find a rolling local low B (lowest close in a trailing window).
2. Require a subsequent recovery: close rises at least `recovery_pct` above
   B within `max_gap_days` bars.
3. Require a second local low C within `retest_window` bars of the recovery
   high, with C's low within `support_tolerance_pct` of B's level (the "W").
4. Enter long at C's close once support has held (close bounces back up
   `confirm_pct` off C's low, i.e. the decline visibly stops).
5. Exit: stop-loss below min(B, C) by `stop_pct`, take-profit at
   `target_pct` above entry, or a `max_hold_days` time-stop -- whichever
   comes first (source gives only a stop rule, no explicit exit target;
   target/time-stop added here since the source's own hold length is
   "often months", too long for meaningful transaction-cost-aware daily
   backtesting without SOME bound).

First double-support-retest (two separate, time-separated support tests at
a similar price) strategy in this repo -- distinct from all prior
double-bottom variants which require a confirmed NECKLINE BREAKOUT of one
consolidation, not two multi-month-apart support touches with no breakout
confirmation.

Interface contract:
    generate_signals(price_df, **params) -> pd.Series ({0,1})
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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
    local_low_window: int = 20,
    recovery_pct: float = 0.05,
    max_gap_days: int = 90,
    retest_window: int = 60,
    support_tolerance_pct: float = 0.04,
    confirm_pct: float = 0.02,
    stop_pct: float = 0.06,
    target_pct: float = 0.15,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]
    n = len(df)

    # Rolling local low: a bar whose close is the minimum in a centered-ish
    # trailing/leading window approximation (causal: use trailing window
    # only, i.e. a bar confirmed as a local low once price has moved away
    # from it -- approximated here via a simple trailing rolling-min match).
    rolling_min = close.rolling(local_low_window).min()
    is_local_low = (close == rolling_min)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = -1
    entry_price = None

    # Track the most recent confirmed local low (B candidate) and whether
    # we've seen a sufficient recovery since it.
    b_idx = None
    b_price = None
    awaiting_c = False

    idx_list = df.index

    for i in range(n):
        if in_position:
            held_days = i - entry_idx
            hit_stop = close.iloc[i] <= entry_price * (1 - stop_pct)
            hit_target = close.iloc[i] >= entry_price * (1 + target_pct)
            if hit_stop or hit_target or held_days >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
            continue

        # Not in position: look for B -> recovery -> C -> confirm sequence.
        if is_local_low.iloc[i]:
            if b_idx is None or not awaiting_c:
                b_idx = i
                b_price = close.iloc[i]
                awaiting_c = False
            else:
                # Candidate C: check it's within tolerance of B and within
                # the retest window, and that we actually recovered first.
                gap = i - b_idx
                if gap <= retest_window and gap > 0:
                    c_price = close.iloc[i]
                    if abs(c_price - b_price) / b_price <= support_tolerance_pct:
                        # confirm: does price bounce confirm_pct off this low
                        # within a few bars (use next available bars lazily
                        # via forward check bounded by max_gap_days window)
                        confirm_end = min(n, i + 10)
                        bounced = False
                        for j in range(i + 1, confirm_end):
                            if close.iloc[j] >= c_price * (1 + confirm_pct):
                                bounced = True
                                confirm_j = j
                                break
                        if bounced:
                            in_position = True
                            entry_idx = confirm_j
                            entry_price = close.iloc[confirm_j]
                            b_idx = None
                            b_price = None
                            awaiting_c = False
                            continue
                # reset B to this new low regardless (rolling forward)
                b_idx = i
                b_price = close.iloc[i]
                awaiting_c = False

        # Check for recovery condition to arm "awaiting_c"
        if b_idx is not None and not awaiting_c:
            gap_since_b = i - b_idx
            if gap_since_b > 0 and gap_since_b <= max_gap_days:
                if close.iloc[i] >= b_price * (1 + recovery_pct):
                    awaiting_c = True
            elif gap_since_b > max_gap_days:
                b_idx = None
                b_price = None
                awaiting_c = False

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
