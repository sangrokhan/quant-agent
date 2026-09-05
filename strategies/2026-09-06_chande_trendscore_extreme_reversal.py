"""Strategy: Chande's TrendScore, extreme-reversal entry rule (long after the
score crosses from -10 up above a recovery threshold).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-103):
Tushar Chande's TrendScore (Stocks & Commodities, Sept 1993): compares
today's close to each of 10 closes from `lag_start` to `lag_start+10` days
ago; +1 per comparison where today's close is higher, -1 where lower,
summed into a score in [-10, +10]. Per a prorealcode.com forum thread
disclosing Chande's own multiple trading-rule variants, one explicit
alternate rule is: "go long after the trendscore crosses from -10 to above
+5 and go short after the trendscore falls from +10 to below 5" -- i.e. an
extreme-reversal entry (must have recently been at the -10 floor, THEN
recover past +5) rather than a simple zero-line cross. This is a novel
indicator family for this repo (no prior TrendScore/Chande Trend Meter
entries in the knowledge base).

Source: https://www.prorealcode.com/topic/request-for-chande-trend-meter/
(quoting Chande's original Sept 1993 Stocks & Commodities article)

Signal logic
------------
- TrendScore[t] = sum over k in [lag_start, lag_start+9] of
  sign(close[t] - close[t-1-k]) (i.e. +1/-1/0 per comparison, standard
  Chande formulation uses lag_start=10 so it compares close[t] against
  close[t-11]..close[t-20]).
- Track whether TrendScore has touched -extreme_floor (e.g. -10) within
  the last `lookback_extreme` bars.
- Entry (long): TrendScore crosses above `recovery_threshold` (e.g. +5)
  AND TrendScore touched -extreme_floor within `lookback_extreme` bars
  prior to this bar (confirms the "recovery from an extreme low" pattern
  the source's rule requires, not just any upward move above +5).
- Exit: TrendScore falls back below `recovery_threshold`, or a
  max_hold_days time-stop.
- Flat otherwise.

Interface contract: both generate_signals and generate_returns accept all
tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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


def _trendscore(close: pd.Series, lag_start: int = 10, lag_window: int = 10) -> pd.Series:
    score = pd.Series(0.0, index=close.index)
    for k in range(lag_start, lag_start + lag_window):
        shifted = close.shift(k + 1)
        score = score + np.sign(close - shifted).fillna(0)
    return score


def generate_signals(
    price_df: pd.DataFrame,
    lag_start: int = 10,
    lag_window: int = 10,
    extreme_floor: float = -10.0,
    recovery_threshold: float = 5.0,
    lookback_extreme: int = 15,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    score = _trendscore(close, lag_start, lag_window)

    touched_floor = score <= extreme_floor
    recently_touched_floor = touched_floor.rolling(lookback_extreme, min_periods=1).max().astype(bool)

    cross_up_recovery = (score > recovery_threshold) & (score.shift(1) <= recovery_threshold)
    entry = (cross_up_recovery & recently_touched_floor.shift(1).fillna(False)).fillna(False)

    exit_signal = (score < recovery_threshold).fillna(False)

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
