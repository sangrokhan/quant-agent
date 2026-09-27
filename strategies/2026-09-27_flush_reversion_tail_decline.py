"""Strategy: single-day "flush" tail-decline reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-076):
Per Dashyan (2026), "The Tail Is the Only Signal: Flush Reversion in Equity
Indices and Crypto Perpetual Futures" (SSRN 7363482, read via browser_exec
this iteration -- web_search DDGS backend intermittently empty on multiple
queries this iteration), after rigorous multiple-testing/date-clustering
corrections across 76 years of US equity index history, only ONE
statistically robust reversal signal survives: a single-day index decline of
<= -7% is followed by a mean NEXT-SESSION return of +3.08%, with the other
nine following sessions averaging ~0.01% (i.e. it is a genuine one-day pop,
not crash-window drift). The paper explicitly reports the SAME mechanism
FAILS completely in crypto perpetuals (edge net of market beta negative in
every regime/year of a 6-year sample) -- this strategy is implemented on
both equity and crypto per this repo's grid-test convention specifically to
document/confirm that documented equity/crypto asymmetry here, not because
the crypto side is expected to pass.

Signal logic
------------
- Compute the single-day close-to-close return.
- Entry (long): today's close-to-close return <= -decline_threshold (a large
  single-day "flush" decline).
- Hold for hold_days trading days (paper's core result is the very next
  session; hold_days is kept tunable for the required parameter grid, with
  1 as the paper's own disclosed base case).
- Flat otherwise. No stacking: if already in a position, an additional
  qualifying decline during the hold does not extend/re-trigger it (paper's
  own event definition also treats overlapping-event clustering as a
  methodological pitfall to correct for, so we deliberately do not stack).

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
    decline_threshold: float = 0.07,
    hold_days: int = 1,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    decline_threshold: magnitude of the single-day decline that triggers
        entry (e.g. 0.07 means close-to-close return <= -7%).
    hold_days: number of trading days to hold the long position after a
        qualifying decline (paper's disclosed base case is 1 -- the very
        next session only).
    """
    df = _prep(price_df)
    close = df["close"]

    daily_ret = close.pct_change()
    trigger = daily_ret <= -abs(decline_threshold)

    position = pd.Series(0, index=close.index, dtype=int)
    held_remaining = 0
    for i in range(len(close)):
        if held_remaining > 0:
            position.iloc[i] = 1
            held_remaining -= 1
        elif bool(trigger.iloc[i]):
            # Enter starting the NEXT bar (position shifted at return-calc
            # time below); mark the trigger bar itself flat, hold_days bars
            # after it long.
            held_remaining = hold_days
            position.iloc[i] = 0
        else:
            position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # position already encodes "flat on trigger day, long on the following
    # hold_days days" -- apply directly (no extra shift needed, since
    # generate_signals already marks the trigger day itself as flat and the
    # subsequent day(s) as long, matching the paper's next-session framing;
    # this avoids look-ahead because entry decision at day i is based only
    # on day i's own already-realized close-to-close return).
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
