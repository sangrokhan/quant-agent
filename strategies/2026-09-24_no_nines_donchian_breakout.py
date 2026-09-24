"""Strategy: Donchian breakout with Bulkowski's "no-nines" delayed-entry filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-130):
Per Thomas Bulkowski's "No-Nines" article (https://thepatternsite.com/NoNines.html,
read via browser_exec, based on Ken Calhoun's Technical Analysis of Stocks &
Commodities Aug-2017 article "Avoiding False Breakouts; No 9s"), professional
traders treat every $10 increment as a price-action resistance level, so
breakouts priced with a "9" as the first digit left of the decimal (e.g.
$29-$29.99, $49-$49.99) more often fail. Bulkowski's own 25-year, 11,077-trade
test across 1,010 stocks found delaying entry until price clears 50 cents
above the next whole dollar (e.g. buy at $50.50 instead of $49.30) modestly
raised average gain (30.0% -> 30.3% for $20-70 stocks, upward breakouts,
Table 1) AND reduced the 5%-failure rate (30.8% -> 30.3%), i.e. a small but
consistent edge from delaying breakout entries with a "9" handle.

Adaptation for this repo: Bulkowski's original test used discretionary chart
patterns (double tops/bottoms, triangles, rectangles) which this repo's
data/loaders.py (plain OHLCV) cannot detect. We adapt the same no-nines LOGIC
to a mechanical, testable breakout: a classic Donchian channel breakout
(long entry when close > rolling N-day high). When the raw breakout day's
close has a "9" as its ones-digit-before-the-decimal (i.e. int(close) % 10
== 9), entry is delayed until a later day's close reaches the "no-nines"
threshold (floor(breakout_close) + 1 + 0.50) -- mirroring Bulkowski's own
$X9.xx -> $(X+1).50 delay rule. If price never reaches that threshold within
a bounded delay window (delay_window days) before instead confirming a new
Donchian exit-window low, the delayed trade is skipped entirely (this is the
mechanism behind Bulkowski's documented failure-rate reduction: false
breakouts that reverse before ever clearing the no-nines threshold are
avoided). Exit uses the classic Donchian exit-window rolling low, or a
max_hold_days time-stop as backstop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 long/flat)
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    entry_window: int = 20,
    exit_window: int = 10,
    delay_window: int = 5,
    no_nines_delay_cents: float = 0.50,
    max_hold_days: int = 40,
    apply_no_nines: bool = True,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Parameters
    ----------
    entry_window : rolling lookback for the Donchian breakout high (raw
        breakout signal day = close > rolling_max(entry_window).shift(1)).
    exit_window : rolling lookback for the Donchian exit low
        (exit day = close < rolling_min(exit_window).shift(1)).
    delay_window : max number of bars to wait for a "9"-handle breakout to
        clear the no-nines threshold before abandoning the delayed trade.
    no_nines_delay_cents : cents above the next whole dollar required before
        entering a delayed ("9"-handle) breakout (Bulkowski's default: 0.50).
    max_hold_days : hard time-stop backstop regardless of exit signal.
    apply_no_nines : if False, degrades to a plain Donchian breakout (used
        as the internal A/B control to isolate the no-nines effect).
    """
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    rolling_entry_high = close.rolling(entry_window).max().shift(1)
    rolling_exit_low = close.rolling(exit_window).min().shift(1)

    raw_breakout = close > rolling_entry_high

    position = pd.Series(0, index=close.index, dtype=int)

    in_position = False
    entry_idx = -1
    pending_breakout_idx = -1  # index of a delayed "9"-handle breakout awaiting confirmation

    close_vals = close.values

    for i in range(n):
        if pending_breakout_idx >= 0:
            # Check if we've waited too long, or price broke back below the
            # exit-window low (invalidating the delayed setup).
            waited = i - pending_breakout_idx
            exit_low_i = rolling_exit_low.iloc[i]
            if waited > delay_window:
                pending_breakout_idx = -1
            elif not math.isnan(exit_low_i) and close_vals[i] < exit_low_i:
                pending_breakout_idx = -1
            else:
                breakout_close = close_vals[pending_breakout_idx]
                threshold = math.floor(breakout_close) + 1 + no_nines_delay_cents
                if close_vals[i] >= threshold and not in_position:
                    in_position = True
                    entry_idx = i
                    pending_breakout_idx = -1

        if not in_position and pending_breakout_idx < 0 and bool(raw_breakout.iloc[i]):
            breakout_close = close_vals[i]
            first_digit_is_nine = apply_no_nines and (int(breakout_close) % 10 == 9)
            if first_digit_is_nine:
                pending_breakout_idx = i
            else:
                in_position = True
                entry_idx = i

        if in_position:
            exit_low_i = rolling_exit_low.iloc[i]
            held_days = i - entry_idx
            hit_exit = (not math.isnan(exit_low_i)) and (close_vals[i] < exit_low_i) and (i > entry_idx)
            hit_time_stop = held_days >= max_hold_days
            if hit_exit or hit_time_stop:
                in_position = False

        position.iloc[i] = 1 if in_position else 0

    return position.astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    entry_window: int = 20,
    exit_window: int = 10,
    delay_window: int = 5,
    no_nines_delay_cents: float = 0.50,
    max_hold_days: int = 40,
    apply_no_nines: bool = True,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs here)."""
    df = _prep(price_df)
    close = df["close"]

    positions = generate_signals(
        price_df,
        entry_window=entry_window,
        exit_window=exit_window,
        delay_window=delay_window,
        no_nines_delay_cents=no_nines_delay_cents,
        max_hold_days=max_hold_days,
        apply_no_nines=apply_no_nines,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = positions.shift(1).fillna(0).astype(int) * daily_returns
    return strat_returns
