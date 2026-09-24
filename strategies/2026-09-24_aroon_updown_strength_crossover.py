"""Strategy: Aroon Up/Down strength-confirmed crossover trend following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-065):
The raw two-line Aroon Up/Aroon Down crossover (distinct from the
single-value Aroon Oscillator already tested extensively in this repo)
measures "freshness of extremes" -- how recently the highest-high/lowest-low
of the lookback window occurred, not the magnitude of price moves. Per
ArrowAlgo's Aroon Crossover Strategy guide
(https://arrowalgo.com/aroon-crossover-strategy/, read this iteration via
browser_exec -- web_search DDGS returning empty results on the initial
Vervoort Smoothed Heikin-Ashi query): the "Strength-Confirmed Entry" variant
(crossover + Aroon Up above a strength threshold of 70, exit when Aroon Up
falls below 50 or the opposite cross) filters out the noisy mid-range
crossovers that a plain Up/Down cross would trigger during chop. First raw
Aroon Up/Down two-line crossover entry in this repo (Aroon Oscillator
single-line already tested 12x with mixed results; this is a distinct
two-line formulation with a different filter shape).

Signal logic
------------
- Aroon Up = 100 * (aroon_period - bars_since_highest_high) / aroon_period
- Aroon Down = 100 * (aroon_period - bars_since_lowest_low) / aroon_period
- Entry (long): Aroon Up crosses above Aroon Down AND Aroon Up >
  entry_strength_threshold (70).
- Exit: Aroon Up falls below exit_threshold (50), OR Aroon Down crosses
  back above Aroon Up, OR a max holding period of max_hold_days.
- Flat (no position) otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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


def _aroon(high: pd.Series, low: pd.Series, aroon_period: int) -> tuple[pd.Series, pd.Series]:
    def bars_since_max(x):
        return len(x) - 1 - np.argmax(x.values)

    def bars_since_min(x):
        return len(x) - 1 - np.argmin(x.values)

    bsh = high.rolling(aroon_period + 1).apply(bars_since_max, raw=False)
    bsl = low.rolling(aroon_period + 1).apply(bars_since_min, raw=False)

    aroon_up = 100.0 * (aroon_period - bsh) / aroon_period
    aroon_down = 100.0 * (aroon_period - bsl) / aroon_period
    return aroon_up, aroon_down


def generate_signals(
    price_df: pd.DataFrame,
    aroon_period: int = 25,
    entry_strength_threshold: float = 70.0,
    exit_threshold: float = 50.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]

    aroon_up, aroon_down = _aroon(high, low, aroon_period)

    up_above_down = aroon_up > aroon_down
    up_above_down_prev = up_above_down.shift(1).fillna(False)
    cross_up = up_above_down & (~up_above_down_prev)
    cross_down = (~up_above_down) & up_above_down_prev

    entry_signal = cross_up & (aroon_up > entry_strength_threshold)

    position = pd.Series(0, index=high.index, dtype=int)
    in_position = False
    hold_days = 0

    idx = high.index
    for i in range(len(idx)):
        if not in_position:
            if bool(entry_signal.iloc[i]):
                in_position = True
                hold_days = 0
        else:
            hold_days += 1
            should_exit = (
                bool(aroon_up.iloc[i] < exit_threshold)
                or bool(cross_down.iloc[i])
                or (hold_days >= max_hold_days)
            )
            if should_exit:
                in_position = False
        position.iloc[i] = 1 if in_position else 0

    position = position.fillna(0).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    aroon_period: int = 25,
    entry_strength_threshold: float = 70.0,
    exit_threshold: float = 50.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        aroon_period=aroon_period,
        entry_strength_threshold=entry_strength_threshold,
        exit_threshold=exit_threshold,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
