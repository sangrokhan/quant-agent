"""Strategy: Even-vs-Odd Calendar-Day Trading Strategy.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-XXX):
Per QuantifiedStrategies.com's "Even Vs. Odd Days Trading Strategy"
(https://www.quantifiedstrategies.com/even-vs-odd-days-trading-strategy/,
Oddmund Groette, read via browser_exec): the S&P 500's gains concentrate
disproportionately on EVEN calendar days of the month (2,4,6,...,30)
rather than ODD calendar days (1,3,5,...,31), based on a close-to-close
buy-and-hold-only-on-that-parity backtest since 1993. The source's own
disclosed rule: "At the close of odd days, we buy the S&P 500 and hold it
until the close of the following even day" (and the symmetric odd-day
strategy). The source itself is candid this is "most likely...the result
of chance" -- included here as an honest, fully falsifiable test of a
source-disclosed numeric rule per RESEARCH_LOOP.md Step 2's requirement
to ground hypotheses in something actually read, not invented; a rejection
here (if it occurs) is exactly as valuable to log as an acceptance.

Zero prior entries for this specific calendar-day-parity mechanism in this
repo's knowledge base (distinct from day-of-WEEK effects like Turnaround
Tuesday/weekend effect, and from day-of-MONTH effects like Turn-of-Month,
which anchor to month-start/end rather than an odd/even numeric parity of
the calendar date itself).

Signal logic
------------
- target_parity: "even" or "odd".
- Position on day t = 1 iff day-of-month(t) has the target parity (i.e.
  the close-to-close return realized ON day t is attributed to holding
  "into" that day from the prior close, matching the source's own
  close-to-close framing: "buy at close of [complementary-parity] day,
  hold until close of the following [target-parity] day").
- Long-only, no leverage (SAFETY.md).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1})
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
    target_parity: str = "even",
) -> pd.Series:
    """Return a {0,1} position series: 1 on days whose calendar
    day-of-month matches `target_parity` ("even" or "odd").
    """
    df = _prep(price_df)
    day_of_month = pd.Series(df.index, index=df.index).dt.day

    if target_parity == "even":
        mask = (day_of_month % 2 == 0)
    elif target_parity == "odd":
        mask = (day_of_month % 2 == 1)
    else:
        raise ValueError("target_parity must be 'even' or 'odd'")

    return mask.astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    target_parity: str = "even",
) -> pd.Series:
    """Close-to-close returns realized only on days matching target_parity."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, target_parity=target_parity)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position * daily_ret
    return strategy_ret.fillna(0.0)
