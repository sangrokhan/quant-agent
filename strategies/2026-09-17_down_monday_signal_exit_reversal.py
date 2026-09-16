"""Strategy: Down-Monday reversal with a SIGNAL-based exit (not fixed hold).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-006):
Per EdgeLab Trading's "Turnaround Tuesday" writeup
(https://edgelabtrading.com/blog/turnaround-tuesday/, read this iteration via
browser_exec -- Substack search results were paywalled), the disclosed exact
rule is: "if Monday closes below the previous trading day's close, buy at
Monday's close. Exit: sell at the first daily close above the previous day's
high." The source reports (QQQ, 2003-2026, 0.05% round-trip commission)
in-sample Sharpe 0.89 / out-of-sample Sharpe 1.17, and near-identical
independent confirmation on SPY (OOS Sharpe 1.23), with time-in-market only
~18-25%.

This repo already has two related-but-distinct entries:
  - 2026-09-08-116 "Down Monday -> Tuesday": same single-down-Monday entry
    condition, but a FIXED 1-day hold exit (sell at Tuesday's close
    regardless of price action). Accepted SPY only, QQQ near-miss.
  - 2026-09-08-135 "Turnaround Tue/Wed 3-day-streak": uses the same
    signal-based exit (close > yesterday's high) as this strategy, but
    requires a 3-CONSECUTIVE-day decline entry trigger on Tue/Wed, not a
    single down-Monday entry.

Neither prior entry tests "single down-Monday entry + signal-based exit"
specifically -- this is the missing combination EdgeLab's own disclosed rule
describes, so it is tested here as a distinct, source-grounded hypothesis
rather than an invented recombination.

Signal logic
------------
- Entry (long): today is Monday AND Monday's close < previous trading day's
  close. Enter at Monday's close.
- Exit: first subsequent day whose close exceeds the PREVIOUS day's high
  (source's exact rule), OR a max_hold_days time-stop backstop (the source
  doesn't disclose one, but an unconditional wait-for-signal exit risks
  indefinite holds through a strong downtrend -- added here as a standard
  risk control, tunable/testable in the grid).
- Flat otherwise (including all non-Monday, non-in-position days).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
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
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    weekday = pd.Series(df.index.weekday, index=df.index)  # Monday=0
    is_monday = weekday == 0
    prev_close = close.shift(1)
    prev_high = high.shift(1)

    down_monday = is_monday & (close < prev_close)
    exit_signal = close > prev_high

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(down_monday.iloc[i]):
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
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias -- can't trade on today's own close).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
