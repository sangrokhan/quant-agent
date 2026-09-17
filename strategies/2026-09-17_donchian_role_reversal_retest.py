"""Strategy: Donchian breakout + role-reversal retest confirmation entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-175):
Per LuxAlgo's "Level Interaction Rules" concept page
(https://www.luxalgo.com/library/concept/level-interaction-rules, read this
iteration via browser_exec after a Google SERP scan): a level's meaning
depends on the FULL interaction sequence, not just the initial touch --
"a break-and-close followed by a held retest argues for role reversal, old
resistance acting as new support." This strategy operationalizes that
sequence mechanically on a rolling Donchian channel: (1) a close breaks
above the rolling N-day high (break-and-close), (2) within a bounded lookback
window afterward, price pulls back and touches back down near that same
former-resistance level (the retest), and (3) that retest HOLDS -- i.e. the
retest bar's low stays within a tolerance band of the level and the bar
closes back above it (a reclaim/held-retest, not a failed break). Only THEN
does the strategy enter long, at the close of the held-retest bar. This is
distinct from every one of this repo's 18+ prior plain Donchian
breakout-on-the-break-itself strategies, which enter immediately on the
break with no retest confirmation requirement -- the retest requirement is
the entire point of this test (does waiting for confirmed role-reversal
produce a higher-quality, lower-whipsaw entry than the raw breakout?).

Signal logic
------------
- Resistance level = rolling N-day high of closes (donchian_window), tracked
  causally (uses data strictly before today).
- Break-and-close: today's close > yesterday's resistance level (first time
  this happens after being flat below it) marks a pending breakout,
  recording the broken level.
- Retest window: for up to retest_max_days bars after the break, watch for
  a bar whose LOW comes back down within retest_tolerance_pct of the broken
  level (a genuine retest touch).
- Held retest (role reversal confirmed): that retest bar's CLOSE is still
  >= the broken level (the level "held" as new support, not a failed
  reclaim-through). Entry is at that bar's close.
- If retest_max_days elapses with no retest touch, OR a retest touch's
  close falls back below the level (failed retest / role reversal did NOT
  happen), the pending breakout is abandoned (no entry) -- this is what
  distinguishes it from an unconditional breakout entry.
- Exit: close falls back below the broken level (support failure) or a
  max_hold_days time-stop.
- Flat otherwise; long-only, single position at a time.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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
    donchian_window: int = 20,
    retest_max_days: int = 10,
    retest_tolerance_pct: float = 0.01,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]
    n = len(close)

    # Causal rolling resistance: highest close over the prior donchian_window
    # bars, NOT including today.
    resistance = close.shift(1).rolling(donchian_window, min_periods=donchian_window).max()

    position = pd.Series(0, index=close.index, dtype=int)

    state = "idle"  # idle -> pending_retest (after break) -> in_position
    broken_level = None
    days_since_break = 0
    in_position = False
    hold_days = 0

    for i in range(n):
        px_close = close.iloc[i]
        px_low = low.iloc[i]
        res = resistance.iloc[i]

        if in_position:
            hold_days += 1
            # Exit on support failure or time-stop.
            if px_close < broken_level or hold_days >= max_hold_days:
                in_position = False
                state = "idle"
                broken_level = None
                hold_days = 0
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        if state == "idle":
            if res == res and px_close > res:
                # Fresh break-and-close above resistance -- start watching
                # for a role-reversal retest.
                state = "pending_retest"
                broken_level = res
                days_since_break = 0
            position.iloc[i] = 0
            continue

        if state == "pending_retest":
            days_since_break += 1
            if days_since_break > retest_max_days:
                # No retest occurred in time -- abandon, no entry.
                state = "idle"
                broken_level = None
                position.iloc[i] = 0
                continue
            tol = broken_level * retest_tolerance_pct
            touched = px_low <= (broken_level + tol)
            if touched:
                if px_close >= broken_level:
                    # Held retest -- role reversal confirmed, enter now.
                    in_position = True
                    state = "in_position"
                    hold_days = 0
                    position.iloc[i] = 1
                else:
                    # Failed retest (closed back below the level) --
                    # role reversal did not hold, abandon.
                    state = "idle"
                    broken_level = None
                    position.iloc[i] = 0
            else:
                position.iloc[i] = 0
            continue

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
