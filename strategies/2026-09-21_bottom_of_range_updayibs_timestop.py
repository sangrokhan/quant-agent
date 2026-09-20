"""Strategy: Bottom-of-the-Range up-day IBS fade with fixed 3-day time-stop.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-178):
Per quantifiedstrategies.com's "The Bottom Of The Range Trading Strategy"
article (https://www.quantifiedstrategies.com/the-bottom-of-the-range-trading-strategy/),
a fully-disclosed and free SPY strategy: IBS = (close-low)/(high-low) < 0.1
(today's bar finished very near its own low, despite closing UP on the day
-- an "up day that finishes near the low of the range", historically
considered a bearish/weak signal by the source's own early-trading-career
anecdote) combined with today's close > yesterday's close (an actual up
day). Entry at today's close, exit after a FIXED 3-day time-stop (not a
signal-based exit like most IBS strategies in this repo). Source's own
backtest (SPY, 2005-present): only 14 trades, 12 winners, avg gain 0.76%,
10.69% cumulative return -- a rare, low-frequency setup.

Distinct from every other IBS entry in this repo: tighter IBS threshold
(0.1 vs the typical 0.15-0.3 used elsewhere), the additional "close >
yesterday's close" up-day filter (most other IBS entries fade an outright
down/weak day, not an up day with a weak intrabar close), and the fixed
time-stop exit (vs. a signal-based exit like "close > prior high" used in
most of this repo's other IBS strategies).

Signal logic
------------
- IBS = (close - low) / (high - low), with the high==low degenerate case
  mapped to IBS=0.5 (undefined range, treated as neutral so it never
  spuriously triggers the low-IBS entry condition).
- Entry (long, at today's close): IBS < ibs_threshold (default 0.1) AND
  close > close.shift(1) (today closed above yesterday's close).
- Exit: after exactly `hold_days` (default 3) trading days from entry
  (fixed time-stop, not a signal-based exit).
- Flat otherwise (no position, and no new entries while already in a
  position).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series
        {0,1} position series aligned to price_df.index.
    generate_returns(price_df, **params) -> pd.Series
        Position-weighted daily returns (position shifted by 1 day to avoid
        look-ahead bias), no transaction costs applied here.
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
    ibs_threshold: float = 0.1,
    hold_days: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    rng = (high - low).replace(0.0, float("nan"))
    ibs = ((close - low) / rng).fillna(0.5)

    entry = (ibs < ibs_threshold) & (close > close.shift(1))
    entry = entry.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
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
