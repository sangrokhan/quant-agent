"""Strategy: Four Consecutive Up Days -> Hold Into Friday's Open (momentum
continuation, not mean reversion).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-117):
Per QuantifiedStrategies.com's "TRADING IDEA - FOUR UP DAYS IN A ROW - S&P
500" (disclosed via Google's AI-overview synthesis of the source, read via
browser_exec fallback -- web_search's DDGS backend errored on this
iteration's queries; the underlying page itself was also checked and found
paywalled/moved, but the concrete rule was independently corroborated by a
Facebook excerpt of the same source ("buying the S&P 500's close after four
consecutive up days and selling Friday's open")): four consecutive daily
up-closes is read as a genuine momentum-continuation signal (the OPPOSITE
economic thesis of every "N consecutive down/up days -> mean reversion"
strategy already tested repeatedly in this repo) -- price enters at the
close of the 4th up day and holds through to the following Friday's open,
regardless of which weekday the signal fires on (so holding period varies
from 1 to 5 trading days depending on where in the week the streak
completes). This is architecturally distinct from every existing
"consecutive days" entry in the knowledge base (all of which are either (a)
consecutive DOWN days as an oversold contrarian long, or (b) consecutive UP
days read as an OVERBOUGHT signal to fade/short) -- here consecutive up
days is the entry trigger for a LONG continuation position with a
calendar-anchored (not signal-based, not fixed N-bar) exit.

Signal logic
------------
For each bar t:
  - Compute the daily up/down close-to-close streak. A "4 consecutive up
    days" event fires when close[t] > close[t-1] > close[t-2] > close[t-3]
    > close[t-4] is NOT required (a naive 4-in-a-row would need 5 bars) --
    the source's literal streak language is: closes[t], closes[t-1],
    closes[t-2], closes[t-3] each higher than the prior day's close (4
    consecutive UP CLOSES, i.e. 4 up-days = 4 positive daily returns in a
    row, requiring 5 bars of price data: t-4..t).
  - On such a signal bar, enter (or stay) long at that day's close.
  - Exit at the *next* Friday's open (if the signal fires on a Friday
    itself, hold through to the FOLLOWING Friday's open, i.e. a full
    week -- source's literal "sell Friday's open" rule, generalized to
    "the first Friday strictly after the signal bar").
  - No trend/regime filter (source's own rule is unconditional -- this
    repo tests the raw, ungated version first per RESEARCH_LOOP.md
    Step 2/4 guidance to ground hypotheses in what was actually read,
    not add untested embellishments).
  - Long-only, single position at a time (no pyramiding on repeated
    signals while already long).

Interface contract for validators (see validation/validators.py) and
grid_test (see validation/grid_test.py):
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        {0, 1} position series aligned to price_df.index.
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Daily strategy returns (position-weighted, no transaction costs
        applied here).

Tunable params (all keyword args, per RESEARCH_LOOP.md Step 5 contract):
    streak_len (default 4)  -- number of consecutive up-closes required to
                                trigger entry.
    exit_weekday (default 4) -- pandas dayofweek convention (Mon=0 ... Fri=4)
                                for the exit-on-open day.
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


def _up_streak(close: pd.Series) -> pd.Series:
    """Length of the current consecutive-up-close streak ending at each bar
    (0 if today's close <= yesterday's close)."""
    up = (close.diff() > 0).astype(int)
    streak = up.copy()
    # Reset-counter cumulative streak using groupby on breaks.
    breaks = (up == 0).cumsum()
    streak = up.groupby(breaks).cumsum()
    return streak


def generate_signals(
    price_df: pd.DataFrame,
    streak_len: int = 4,
    exit_weekday: int = 4,  # Friday
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    idx = close.index

    streak = _up_streak(close)
    entry_signal = streak >= streak_len

    position = pd.Series(0, index=idx, dtype=int)
    pos = 0
    exit_target_date = None  # the Friday (or later, if holiday) date we exit on the OPEN of

    dayofweek = pd.Series(idx.dayofweek if hasattr(idx, "dayofweek") else pd.to_datetime(idx).dayofweek, index=idx)

    for i in range(len(idx)):
        today = idx[i]

        # Exit check first: if we're long and today's bar IS the exit day
        # (today >= the scheduled exit date), flatten "at the open" -- we
        # approximate this by flattening at the START of this bar, i.e.
        # today's return is NOT captured (position recorded as 0 for today).
        if pos == 1 and exit_target_date is not None and today >= exit_target_date:
            pos = 0
            exit_target_date = None

        # Record position for today BEFORE considering a new entry signal
        # triggered by today's close (that entry only takes effect from
        # tomorrow onward, handled naturally by generate_returns' shift).
        position.iloc[i] = pos

        if pos == 0 and bool(entry_signal.iloc[i]):
            pos = 1
            # find first Friday (exit_weekday) strictly after today
            dow_today = dayofweek.iloc[i]
            days_ahead = (exit_weekday - dow_today) % 7
            if days_ahead == 0:
                days_ahead = 7  # if signal itself fires on Friday, go to NEXT Friday
            exit_target_date = today + pd.Timedelta(days=days_ahead)

    return position.fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    streak_len: int = 4,
    exit_weekday: int = 4,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(price_df, streak_len=streak_len, exit_weekday=exit_weekday)
    # Position already represents "held during this bar" (entry decided at
    # yesterday's close is applied as of today per the loop's flow -- but to
    # avoid look-ahead we still shift by 1, consistent with every other
    # strategy in this repo: position[t] uses info through close[t], and is
    # applied to return[t+1].
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
