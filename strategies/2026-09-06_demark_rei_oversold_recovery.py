"""Strategy: DeMark Range Expansion Index (REI) oversold-recovery.

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Per Enlightened Stock Trading's REI guide and QuantifiedStrategies.com's
REI article (both newly visited this iteration), Tom DeMark's Range
Expansion Index (published in "The New Science of Technical Analysis",
1994) is an arithmetically-calculated momentum oscillator (-100 to +100)
measuring the ratio of "strong" price changes to total price changes over
a lookback window (default 8 bars), with overbought above +60 and oversold
below -60. Enlightened Stock Trading's own stated rules-based strategy:
"Entry Rule: Buy when the indicator crosses above -60 after being
oversold. Exit Rule: Sell after 100 for four consecutive days or when REI
crosses back below +60." First DeMark REI strategy in this repo -- distinct
from every other momentum oscillator already tested because REI is
arithmetically (not exponentially) weighted specifically to reduce the
large recent-data-weighted swings DeMark criticized in MACD-style
oscillators, per the source's own comparison table.

DeMark's exact proprietary REI formula (which strong/weak price-change
classification uses several nested conditional look-back comparisons) is
not fully disclosed in either free source (QuantifiedStrategies' numeric
backtest code is paywalled). This repo therefore uses a widely-documented,
simpler arithmetic approximation matching the sources' own description
("ratio of strong price changes to total price changes"):
    strong_change[i] = (high[i] - high[i-2]) + (low[i] - low[i-2])
    total_change[i]  = abs(high[i] - high[i-2]) + abs(low[i] - low[i-2])
    REI = 100 * rolling_sum(strong_change, window) / rolling_sum(total_change, window)
This is a transparent operationalization, not a literal reproduction of
DeMark's original algorithm -- flagged explicitly per RESEARCH_LOOP.md's
novelty/sourcing requirements.

Signal logic
------------
- REI(rei_window) as above (default window=8, DeMark's canonical setting).
- Entry (long): REI was below `oversold_threshold` (-60) at some point in
  the last `oversold_lookback` bars, and today's REI crosses back above
  `oversold_threshold` (the source's literal "crosses above -60 after
  being oversold" rule).
- Exit: REI crosses back below `overbought_threshold` (+60, the source's
  literal exit condition) after having been above it, OR REI has been
  at/above a `confirm_level` (100 canonically, tunable) for
  `confirm_hold_days` consecutive bars (source's "sell after 100 for four
  consecutive days" rule), OR a `max_hold_days` time-stop backstop.
- Long-only, flat otherwise.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _rei(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    strong_change = (high - high.shift(2)) + (low - low.shift(2))
    total_change = (high - high.shift(2)).abs() + (low - low.shift(2)).abs()
    num = strong_change.rolling(window).sum()
    den = total_change.rolling(window).sum().replace(0, np.nan)
    rei = 100.0 * num / den
    return rei.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    rei_window: int = 8,
    oversold_threshold: float = -60.0,
    overbought_threshold: float = 60.0,
    oversold_lookback: int = 5,
    confirm_level: float = 100.0,
    confirm_hold_days: int = 4,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(df)

    rei = _rei(df, rei_window)
    was_oversold = (rei < oversold_threshold).rolling(oversold_lookback).max().astype(bool)
    was_oversold_prev = was_oversold.shift(1).fillna(False)
    entry_trigger = (rei >= oversold_threshold) & (rei.shift(1) < oversold_threshold) & was_oversold_prev

    exit_overbought_cross = (rei < overbought_threshold) & (rei.shift(1) >= overbought_threshold)
    confirm_run = (rei >= confirm_level).rolling(confirm_hold_days).sum() >= confirm_hold_days

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    hold_count = 0
    was_above_ob = False
    for i in range(n):
        if in_pos:
            hold_count += 1
            if bool(rei.iloc[i] >= overbought_threshold):
                was_above_ob = True
            ec = bool(exit_overbought_cross.iloc[i]) and was_above_ob
            cf = bool(confirm_run.iloc[i]) if pd.notna(confirm_run.iloc[i]) else False
            if ec or cf or hold_count >= max_hold_days:
                in_pos = False
                was_above_ob = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            entered = bool(entry_trigger.iloc[i]) if pd.notna(entry_trigger.iloc[i]) else False
            if entered:
                in_pos = True
                hold_count = 0
                was_above_ob = False
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    rei_window: int = 8,
    oversold_threshold: float = -60.0,
    overbought_threshold: float = 60.0,
    oversold_lookback: int = 5,
    confirm_level: float = 100.0,
    confirm_hold_days: int = 4,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        rei_window=rei_window,
        oversold_threshold=oversold_threshold,
        overbought_threshold=overbought_threshold,
        oversold_lookback=oversold_lookback,
        confirm_level=confirm_level,
        confirm_hold_days=confirm_hold_days,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
