"""Strategy: Darvas Box breakout (Nicolas Darvas, 1950s-60s).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-054):
Per tradingsim.com's "Darvas Box Trading Strategy: Complete Guide" article,
Darvas's original mechanical rule set is:
  1. A stock makes a new N-day (Darvas used 52-week) high.
  2. After that high, there are `confirm_days` consecutive days that do NOT
     exceed the high (consolidation confirms the box).
  3. The new high becomes the TOP of the box; the lowest low during those
     confirmation days becomes the BOTTOM of the box.
  4. Buy on a close that breaks above the box top.
  5. Sell/exit if a close breaches the box bottom (stop), or a new box
     re-forms lower (regime change), or (our addition, since Darvas himself
     traded with no fixed time exit) a max_hold_days time-stop to bound risk.

This is mechanically distinct from the already-tested N-day Donchian
breakout family (2026-09-03-008 plain, 2026-09-04-054 Turtle asymmetric
20/10): Donchian's stop/exit is simply a shorter rolling low, continuously
recomputed every bar. Darvas's box is a *discrete, event-triggered*
consolidation range that only re-forms after a NEW high is set and then
confirmed by `confirm_days` of non-exceedance -- the box stays fixed
(top/bottom frozen) between those re-formation events, rather than
Donchian's continuously-rolling channel. The "3 consecutive days not
exceeding the prior high" confirmation gate has no analog in the previously
tested Donchian variants.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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
    high_lookback: int = 52,
    confirm_days: int = 3,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series implementing Darvas boxes.

    Mechanical operationalization of Darvas's rules on daily bars:
      - `high_lookback`: window (trading days) used to define a "new high"
        (Darvas's original 52-week high -> ~252 trading days; we default to
        52 trading days ~10 weeks as a shorter, more frequently-triggering
        analog suitable for backtesting a handful of years of daily data,
        and expose it as a tunable grid parameter).
      - `confirm_days`: number of consecutive days after the high that must
        NOT exceed it, to confirm the box (Darvas's rule: 3).
      - Box top = the triggering new high; box bottom = the lowest low
        observed during the `confirm_days` confirmation window.
      - Entry: close breaks above box top (breakout buy).
      - Exit: close breaches box bottom (box breakdown stop), OR a new box
        top/bottom pair forms while in position (regime re-set), OR
        `max_hold_days` time-stop.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close
    n = len(close)

    rolling_high = high.rolling(high_lookback).max()
    is_new_high = high >= rolling_high  # today's high ties/sets the rolling max

    position = pd.Series(0, index=close.index, dtype=int)

    box_top = None
    box_bottom = None
    box_pending_high_idx = None  # index of the candidate new high awaiting confirmation
    confirm_count = 0
    in_position = False
    entry_idx = 0

    for i in range(n):
        # --- box (re)formation state machine ---
        if box_pending_high_idx is not None:
            if float(high.iloc[i]) > float(high.iloc[box_pending_high_idx]):
                # new high broke the pending candidate before confirmation -> restart candidate
                box_pending_high_idx = i
                confirm_count = 0
            else:
                confirm_count += 1
                if confirm_count >= confirm_days:
                    box_top = float(high.iloc[box_pending_high_idx])
                    lo_slice = low.iloc[box_pending_high_idx : i + 1]
                    box_bottom = float(lo_slice.min())
                    box_pending_high_idx = None
                    confirm_count = 0
        if bool(is_new_high.iloc[i]) and box_pending_high_idx is None:
            box_pending_high_idx = i
            confirm_count = 0

        # --- trading logic ---
        c = float(close.iloc[i])
        if in_position:
            held = i - entry_idx
            breakdown = box_bottom is not None and c < box_bottom
            if breakdown or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if box_top is not None and c > box_top:
                in_position = True
                entry_idx = i
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
