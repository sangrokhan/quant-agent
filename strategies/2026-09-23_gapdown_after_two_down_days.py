"""Strategy: Unfilled gap-down preceded by 2 consecutive down days (3-day
capitulation-then-gap pattern), fixed time-stop exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-XXX):
Per QuantifiedStrategies.com's "Unfilled Gap Trading Strategies"
(https://www.quantifiedstrategies.com/unfilled-gap-trading-strategies/,
read via browser_exec this iteration -- web_search DDGS/Yahoo backend
TLS-errored on every query attempted), source discloses a specific 3-
condition AND-gate variant distinct from the plain RSI-filtered unfilled
gap-down already tested and rejected in this repo (2026-09-11-084, "unfilled
gap-down + RSI(10)<50", rejected -- best config was generic upward drift
over a 10-day hold, not a genuine gap-reversal edge): (1) two trading days
ago was a down day close-to-close, (2) yesterday was ALSO a down day
close-to-close, (3) today is an unfilled gap-down (today's high < yesterday's
low). If all 3 are true, enter long at today's close; exit after a fixed
holding period. This is a genuine capitulation-exhaustion pattern (a
2-day-down-streak immediately followed by a gap-down, i.e. THREE
consecutive down days with the third being a full unfilled gap) rather
than a single-indicator threshold filter -- structurally distinct from the
RSI-gated variant already rejected.

Signal logic
------------
- Down day: close < prior close.
- Unfilled gap-down: today's high < yesterday's low.
- Entry (long): 2 consecutive down days (t-2, t-1) followed by an unfilled
  gap-down on day t. Enter at close of day t.
- Exit: after a fixed hold_days holding period (source's own construction
  tests hold_days from 1 to 20; no early exit rule disclosed).

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
    hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    down_day = close < close.shift(1)
    two_days_ago_down = down_day.shift(1)
    one_day_ago_down = down_day.shift(0)  # will be re-referenced below

    # today's high < yesterday's low (unfilled gap-down)
    unfilled_gap_down = high < low.shift(1)

    # entry condition: t-2 down, t-1 down, t is unfilled gap-down
    down_t_minus_2 = down_day.shift(2)
    down_t_minus_1 = down_day.shift(1)
    entry = down_t_minus_2.fillna(False) & down_t_minus_1.fillna(False) & unfilled_gap_down.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
