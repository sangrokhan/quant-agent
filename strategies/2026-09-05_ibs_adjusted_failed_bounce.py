"""Strategy: IBS "Adjusted Failed Bounce" dip-buy (Rob Hanna, adapted).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-019):
Per CoinGecko's summary of Rob Hanna's "Adjusted Failed Bounce" strategy
(Internal Bar Strength, IBS = (Close-Low)/(High-Low)), a dead-cat-bounce
pattern in an established short-term downtrend is a mean-reversion long
entry setup. Concrete 4-condition rule:

1. Yesterday's IBS >= ibs_threshold (0.6 default) -- yesterday closed
   strong relative to its own range (the "bounce" that then fails).
2. Yesterday's low was below the lowest low of the `lookback` days before
   yesterday (a fresh short-term low was set).
3. Today's close is below yesterday's close (the bounce fails -- price
   resumes falling).
4. Exit when close rises above the highest high of the `lookback` days
   before entry (source's own exit rule), or a max_hold_days time-stop
   backstop (this repo's convention, since the source gives no hard
   maximum hold).

Distinct from all prior IBS-family strategies tested in this repo
(2026-09-04-089/158/159/164, all simple IBS<threshold / IBS-average
oversold entries) -- this uses a structurally different 4-condition
failed-bounce pattern (a fresh low + a strong close the day before + a
weak close today), not a bare IBS threshold cross.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position series)
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
    ibs_threshold: float = 0.6,
    lookback: int = 5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    rng = (high - low).replace(0, pd.NA)
    ibs = (close - low) / rng
    ibs = ibs.astype(float)

    # Condition 1: yesterday's IBS >= threshold.
    cond1 = ibs.shift(1) >= ibs_threshold
    # Condition 2: yesterday's low < lowest low of the `lookback` days
    # before yesterday (i.e. days t-lookback-1 .. t-2).
    prior_low_min = low.shift(2).rolling(lookback).min()
    cond2 = low.shift(1) < prior_low_min
    # Condition 3: today's close < yesterday's close.
    cond3 = close < close.shift(1)

    entry = (cond1 & cond2 & cond3).fillna(False)

    # Exit reference: highest high of the `lookback` days before entry,
    # fixed at the entry bar (source's own exit rule).
    entry_hh_series = high.shift(1).rolling(lookback).max()

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_hh = None
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_target_hit = entry_hh is not None and close.iloc[i] > entry_hh
            if exit_target_hit or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                entry_hh = entry_hh_series.iloc[i]
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
