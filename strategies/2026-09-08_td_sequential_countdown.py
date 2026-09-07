"""Strategy: TD Sequential Setup + simplified Countdown confirmation
(Tom DeMark), long-only buy-exhaustion variant.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
per https://pinescriptforge.com/strategy/td-sequential, TD Sequential
counts consecutive closes above/below the close 4 bars prior. A completed
"TD Buy Setup" (9 consecutive closes each lower than the close 4 bars
prior) signals selling exhaustion, but the source explicitly notes "TD
Countdown is a stronger signal" -- a secondary confirmation count (13
bars where close <= the low 2 bars prior, cumulative, not necessarily
consecutive) that must ALSO complete before the Setup's reversal signal is
considered high-confidence. This directly follows up on this repo's
already-rejected simple 9-count-only TD Buy Setup (2026-09-04-032) by
adding the Countdown confirmation layer the source says is the stronger
signal, testing whether the extra confirmation (fewer, higher-quality
signals) rescues the previously-rejected idea.

Signal logic
------------
- TD Setup count: consecutive count of bars where close < close 4 bars
  prior (a "buy setup" building block); a completed Setup = count reaches
  setup_count (9, standard).
- TD Countdown count (simplified proxy, not the full DeMark recursion
  with setup-cancellation/qualifying conditions): starting the bar AFTER
  a completed Setup, count (cumulatively, can skip bars) how many bars
  have close <= low 2 bars prior; a completed Countdown = count reaches
  countdown_count (13, standard).
- Entry (long): on the bar the Countdown completes (stronger, rarer
  signal than Setup alone).
- Exit: close crosses back above a short SMA (recovery confirmation,
  same convention as this repo's already-tested simple TD Setup
  strategy), or a max_hold_days time-stop.
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
    setup_just_completed = False
    countdown_progress = 0
    countdown_active = False

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_days = 0

    for i in range(n):
        c = close.iloc[i]
        s = sma.iloc[i]

        # --- TD Setup counting (needs i>=4 for the 4-bars-prior comparison) ---
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
        else:
            setup_just_completed = False

        # --- TD Countdown counting (simplified: cumulative close<=low[2]) ---
        countdown_completed_now = False
        if countdown_active and i >= 2:
            if c <= low.iloc[i - 2]:
                countdown_progress += 1
                if countdown_progress >= countdown_count:
                    countdown_completed_now = True
                    countdown_active = False
                    countdown_progress = 0

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
