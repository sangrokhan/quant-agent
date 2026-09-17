"""Strategy: F. Arden Thomas Voting With Multiple Timeframes (stochastic vote).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-159):
F. Arden Thomas's article (TASC Aug 2020, Traders' Tips code republished
Nov 2020, source: Traders.com Nov 2020 Traders' Tips, TradeStation
EasyLanguage code read this iteration) computes a stochastic oscillator
independently across SEVEN different timeframes (all derived from the daily
bar stream by taking every Nth close: weekly=5d, "bimonthly"=10d,
monthly=21d, "quarter-quarter"=15d, "half-quarter"=31d, quarter=63d, plus
the raw daily stochastic) and produces a vote count: BuyPressure = number of
timeframes currently oversold, SellPressure = number currently overbought.
The idea is that when MANY independent timeframes simultaneously agree the
market is oversold (high BuyPressure), that's a stronger, more broadly
confirmed reversal signal than any single-timeframe stochastic reading.
This is a genuinely novel N-timeframe (N=7) voting mechanic, distinct from
this repo's existing 2-3-timeframe alignment strategies (e.g. Elder Triple
Screen, daily/weekly/monthly RSI alignment) which require STRICT ordering
agreement rather than a majority-vote count.

Formula (per source)
---------------------
For each of the 7 timeframes (subsample interval N in trading days:
{5, 10, 15, 21, 31, 63} plus the raw daily series), build a subsampled
close series (only updates every N bars, held flat between updates -- a
faithful reproduction of the EasyLanguage `Mod(CurrentBar, N)=0` sampling),
then compute a `stochastic_length`-period %K stochastic on that subsampled
series: %K = (Close - LowestClose) / (HighestClose - LowestClose) * 100.
- BuyPressure(t) = count of the 7 timeframe-stochastics below `oversold`.
- SellPressure(t) = count of the 7 timeframe-stochastics above `overbought`.

Signal logic (adaptation to a testable trading rule; original article's
Traders' Tips code is display-only, no explicit trading rule)
------------------------------------------------------------------------
- Entry (long): BuyPressure >= `buy_threshold` (broad oversold agreement
  across many timeframes).
- Exit: SellPressure >= `sell_threshold` (broad overbought agreement),
  OR after `max_hold_days`.
- No short leg.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_TIMEFRAMES = [5, 10, 15, 21, 31, 63]  # weekly, bimonthly, quarter-quarter, monthly, half-quarter, quarter
_ALL_TIMEFRAMES = [1] + _TIMEFRAMES  # 1 = raw daily


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _subsampled_stoch(close: pd.Series, n_days: int, stoch_length: int) -> pd.Series:
    """Take every n_days-th close (bar-index modular sampling, like the
    EasyLanguage Mod(CurrentBar, N)=0 condition), hold flat between updates,
    then compute a stoch_length-period %K stochastic on that subsampled
    series, forward-filled back onto the original daily index."""
    n = len(close)
    idx_positions = np.arange(n)
    sample_mask = (idx_positions % n_days) == 0
    sampled = close.where(sample_mask).ffill()

    # %K computed on the (flat-between-updates) subsampled series, using a
    # rolling window measured in *subsample events* -- approximate by using
    # a rolling window of stoch_length * n_days calendar bars over the
    # subsampled series (equivalent to stoch_length subsample points).
    window = stoch_length * n_days
    lowest = sampled.rolling(window, min_periods=window).min()
    highest = sampled.rolling(window, min_periods=window).max()
    rng = (highest - lowest).replace(0, np.nan)
    pct_k = (sampled - lowest) / rng * 100
    return pct_k


def generate_signals(
    price_df: pd.DataFrame,
    stoch_length: int = 21,
    overbought: float = 80.0,
    oversold: float = 20.0,
    buy_threshold: int = 5,
    sell_threshold: int = 4,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    buy_pressure = pd.Series(0, index=close.index, dtype=int)
    sell_pressure = pd.Series(0, index=close.index, dtype=int)
    for n_days in _ALL_TIMEFRAMES:
        stoch = _subsampled_stoch(close, n_days, stoch_length)
        buy_pressure = buy_pressure + (stoch < oversold).fillna(False).astype(int)
        sell_pressure = sell_pressure + (stoch > overbought).fillna(False).astype(int)

    entry = buy_pressure >= buy_threshold
    exit_signal = sell_pressure >= sell_threshold

    warmup = max(_ALL_TIMEFRAMES) * stoch_length

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if i < warmup:
            position.iloc[i] = 0
            continue
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
