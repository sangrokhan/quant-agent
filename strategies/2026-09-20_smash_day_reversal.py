"""Strategy: Larry Williams' Smash Day Reversal (buy-stop entry, structural stop exit).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-132):
Per Larry Williams' classic "Smash Day" pattern (widely documented, e.g.
https://www.google.com/search?q=Larry+Williams+%22Smash+Day%22+reversal+pattern+rules+specific
Google AI-overview synthesis this iteration, and The Rogue Quant's Substack
"I Backtested Larry Williams' Trading Strategy Across 15 Markets" -- both
visited via browser_exec this iteration; web_search failed several queries
this iteration with rustls TLS-EOF errors requiring the browser fallback):
a "Smash Day" occurs when today's close breaks BELOW yesterday's low --
"what should happen (trend continuation) doesn't happen", i.e. a violent
one-day emotional overshoot to the downside that closes weak but sets up a
mean-reversion trap for late shorts. The trading rule is NOT to buy the
Smash Day itself, but to place a buy-STOP at the Smash Day's own HIGH: if
price rallies enough the very next session to clear that high, it confirms
the overshoot was a false move and triggers a long entry. Exit uses the
source's own structural stop: if price instead trades below the Smash
Day's LOW after entry, the reversal thesis is invalidated and the position
is stopped out. This is the first Smash Day / buy-stop-above-yestertday's-
extreme-day-high pattern tested in this repo (distinct from Turtle Soup,
which fades a failed N-day-low breakdown with an IMMEDIATE same/next-bar
close-based re-entry rather than a stop-order trigger on the reversal
day's own high, and distinct from Key Reversal Day and Island Reversal,
which use different single/multi-bar gap structures).

Signal logic
------------
- Smash Day (day t): close[t] < low[t-1] (today closed below yesterday's low).
- Entry trigger (day t+1): if high[t+1] >= high[t] (price rallies enough
  next session to clear the Smash Day's own high -- simulating a buy-stop
  order placed at that level), enter long. Approximated here on daily bars
  as "trigger day's high clears the Smash Day's high" (can't model
  intraday stop fills exactly with EOD OHLC data, but this captures the
  same condition the buy-stop would fire on).
- Exit: close falls below the Smash Day's own low (structural stop,
  source's own rule) OR a max_hold_days time-stop backstop (this repo's
  standard safety addition, not in the original source) OR profit target
  at entry + target_r_mult * (smash_day_high - smash_day_low) (adds a
  defined reward target since the bare source rule has no explicit take-
  profit, only the structural stop).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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
    target_r_mult: float = 2.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    smash_day = (close < low.shift(1)).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_level = 0.0
    target_level = 0.0

    smash_high = None
    smash_low = None

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            stopped_out = close.iloc[i] < stop_level
            hit_target = close.iloc[i] >= target_level
            time_out = held >= max_hold_days
            if stopped_out or hit_target or time_out:
                in_position = False
                position.iloc[i] = 0
                smash_high = None
                smash_low = None
                continue
            position.iloc[i] = 1
        else:
            # Check if we have a pending Smash Day from yesterday, and
            # today's high clears it (buy-stop trigger).
            if smash_high is not None and high.iloc[i] >= smash_high:
                in_position = True
                entry_idx = i
                stop_level = smash_low
                target_level = smash_high + target_r_mult * (smash_high - smash_low)
                position.iloc[i] = 1
                smash_high = None
                smash_low = None
            else:
                position.iloc[i] = 0
                # Register today as a fresh Smash Day for tomorrow's check
                # (only if not already carrying a pending one -- take the
                # most recent Smash Day if several occur in a row).
                if bool(smash_day.iloc[i]):
                    smash_high = high.iloc[i]
                    smash_low = low.iloc[i]
                elif smash_high is not None:
                    # Pending Smash Day from a prior bar that hasn't
                    # triggered yet -- keep waiting (no expiry in source's
                    # rule, but cap the wait implicitly since a fresh
                    # Smash Day would overwrite it above).
                    pass
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
