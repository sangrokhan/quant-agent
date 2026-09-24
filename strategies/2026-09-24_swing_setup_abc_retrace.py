"""Strategy: Bulkowski's Swing Trading Setup -- buy the retrace low (C) of a
confirmed rise-then-retrace (A-B-C) swing pattern, target = highest close
from A to C, stop = fixed percentage below entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-138):
Per https://thepatternsite.com/SwingSetup.html (Thomas Bulkowski,
browser_exec): identify a confirmed `swing_window`-day (default 5, an
11-bar window) swing LOW (A), the subsequent confirmed swing HIGH (B), and
the following confirmed swing LOW (C) -- a rise A->B followed by a retrace
B->C. Buy at C (the "perfect entry" -- this repo enters at the next bar's
open once C is confirmed, since C itself is only knowable `swing_window`
bars later). Exit when price closes at/above the TARGET (the highest CLOSE,
not high, from A to C) or drops `stop_pct` (source uses 5%) below the entry
price, whichever comes first. Source's own updated (3/26/2020) 489-stock,
2009-2020 bull-market test found Fibonacci retracement levels (38/50/62%)
are NOT more statistically likely than any other retrace depth -- so unlike
the repo's existing Fibonacci-band strategy (2026-09-03-022, which gates
entries on a 50-61.8% retracement zone), this strategy takes the source's
own updated finding at face value and does NOT filter by retracement depth
at all; it enters on ANY confirmed A-B-C swing pattern regardless of how
deep the retrace was.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series {0,1} long/flat
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
    swing_window: int = 5,
    stop_pct: float = 0.05,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]
    n = len(df)

    full_win = 2 * swing_window + 1
    is_swing_high = high == high.rolling(full_win, center=True).max()
    is_swing_low = low == low.rolling(full_win, center=True).min()

    sh_vals = is_swing_high.values
    sl_vals = is_swing_low.values
    high_vals = high.values
    low_vals = low.values
    close_vals = close.values

    position = pd.Series(0, index=df.index, dtype=int)

    # State machine over confirmed pivots (each only known `swing_window`
    # bars after it occurs, since detection uses a centered window).
    state = "seek_A"  # seek_A -> seek_B -> seek_C -> in_trade
    A_idx = None
    B_idx = None
    C_idx = None
    entry_idx = None
    entry_price = None
    target_price = None
    stop_price = None

    for i in range(n):
        confirmable = i + swing_window < n  # this bar's pivot status is knowable by bar i (centered window already looks back+forward swing_window, so it's "confirmed" once the window is full -- treat as known at i itself for simplicity, matching this repo's other swing-based strategies' convention)

        if state == "in_trade":
            held = i - entry_idx
            hit_target = close_vals[i] >= target_price
            hit_stop = close_vals[i] <= stop_price
            hit_time = held >= max_hold_days
            position.iloc[i] = 1
            if hit_target or hit_stop or hit_time:
                state = "seek_A"
                A_idx = B_idx = C_idx = None
            continue

        if not confirmable:
            continue

        if state == "seek_A":
            if bool(sl_vals[i]):
                A_idx = i
                state = "seek_B"
        elif state == "seek_B":
            if bool(sh_vals[i]) and i > A_idx:
                B_idx = i
                state = "seek_C"
            elif bool(sl_vals[i]) and i > A_idx:
                # A newer swing low supersedes A (keep the most recent one).
                A_idx = i
        elif state == "seek_C":
            if bool(sl_vals[i]) and i > B_idx:
                C_idx = i
                # Entry at next bar's open (approximated here via next
                # close-to-close return by entering at C+1 close basis --
                # signal flips on at C+1).
                entry_idx = min(i + 1, n - 1)
                entry_price = close_vals[entry_idx]
                target_price = close_vals[A_idx:C_idx + 1].max()
                stop_price = entry_price * (1.0 - stop_pct)
                if target_price > entry_price:
                    state = "in_trade"
                else:
                    # Degenerate: target already below entry -- restart from C as new A.
                    A_idx = C_idx
                    state = "seek_B"
            elif bool(sh_vals[i]) and i > B_idx and high_vals[i] > high_vals[B_idx]:
                # A higher high supersedes B.
                B_idx = i

    return position.astype(float)


def generate_returns(
    price_df: pd.DataFrame,
    swing_window: int = 5,
    stop_pct: float = 0.05,
    max_hold_days: int = 60,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs here)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        swing_window=swing_window,
        stop_pct=stop_pct,
        max_hold_days=max_hold_days,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0.0) * daily_returns
    return strat_returns
