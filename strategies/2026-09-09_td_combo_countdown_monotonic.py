"""Strategy: TD Combo (Tom DeMark) -- Setup + monotonic-decline Countdown,
long-only buy-exhaustion variant.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-031):
Per Google AI-overview synthesis of Scribd/TradingView/Anahit.ai material on
DeMark's TD Combo indicator (read this cron trigger, see
knowledge_base/visited_pages.jsonl entry for
"DeMark+TD+Combo+indicator+specific+trading+rules+setup+countdown"), TD
Combo's Buy Setup phase is identical to plain TD Sequential (9 consecutive
closes below the close 4 bars prior -- already tested/rejected in this repo
as 2026-09-04-032). What's genuinely DIFFERENT is the Countdown phase: TD
Combo's Countdown, unlike TD Sequential's Countdown (already tested with a
simplified proxy as 2026-09-08-079, near-miss QQQ Sharpe 0.974), imposes an
explicit MONOTONIC-DECLINE constraint -- each qualifying countdown bar's low
must be lower than the PRIOR qualifying countdown bar's low, not just
satisfy the close<=low[2] condition in isolation. This is a materially
stricter, path-dependent counting rule (a true "lower low each time"
requirement) that should produce fewer but higher-conviction signals than
either the plain Setup (2026-09-04-032, rejected) or the Sequential
Countdown proxy (2026-09-08-079, near-miss).

Signal logic
------------
- TD Setup count: consecutive count of bars where close < close 4 bars
  prior; a completed Setup = count reaches setup_count (9, standard).
- TD Combo Countdown count (distinct from Sequential's Countdown): starting
  the bar AFTER a completed Setup, count (cumulatively, can skip bars) how
  many bars have BOTH (a) close <= low 2 bars prior, AND (b) this bar's low
  is strictly lower than the low of the last bar that incremented the
  countdown (monotonic-decline requirement, TD Combo's defining feature
  vs. plain TD Sequential Countdown). A completed Countdown = count reaches
  countdown_count (13, standard).
- Entry (long): on the bar the Countdown completes.
- Exit: close crosses back above a short SMA (recovery confirmation, same
  convention as this repo's other TD-family strategies), or a
  max_hold_days time-stop.
- Flat otherwise.

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
    setup_count: int = 9,
    countdown_count: int = 13,
    exit_sma_period: int = 10,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]
    sma = close.rolling(exit_sma_period).mean()

    n = len(df.index)
    setup_streak = 0
    countdown_progress = 0
    countdown_active = False
    last_countdown_low = None

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_days = 0

    for i in range(n):
        c = close.iloc[i]
        lo = low.iloc[i]
        s = sma.iloc[i]

        # --- TD Setup counting (needs i>=4 for the 4-bars-prior comparison) ---
        setup_just_completed = False
        if i >= 4:
            if c < close.iloc[i - 4]:
                setup_streak += 1
            else:
                setup_streak = 0
            setup_just_completed = setup_streak == setup_count
            if setup_just_completed:
                setup_streak = 0
                countdown_active = True
                countdown_progress = 0
                last_countdown_low = None

        # --- TD Combo Countdown counting: close<=low[2] AND monotonic
        # lower-low vs the last qualifying countdown bar's low ---
        countdown_completed_now = False
        if countdown_active and i >= 2:
            qualifies_close = c <= low.iloc[i - 2]
            qualifies_lower_low = (last_countdown_low is None) or (lo < last_countdown_low)
            if qualifies_close and qualifies_lower_low:
                countdown_progress += 1
                last_countdown_low = lo
                if countdown_progress >= countdown_count:
                    countdown_completed_now = True
                    countdown_active = False
                    countdown_progress = 0
                    last_countdown_low = None

        # --- position management ---
        if in_position:
            hold_days += 1
            if (not pd.isna(s) and c > s) or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
            else:
                position.iloc[i] = 1
        else:
            if countdown_completed_now:
                in_position = True
                hold_days = 1
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    setup_count: int = 9,
    countdown_count: int = 13,
    exit_sma_period: int = 10,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_returns = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        setup_count=setup_count,
        countdown_count=countdown_count,
        exit_sma_period=exit_sma_period,
        max_hold_days=max_hold_days,
    )
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns
