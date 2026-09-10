"""Strategy: SMA200 upcross entry with layered SMA200/Donchian-low trailing exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-044):
Per SetupAlpha's "I Tested 56 Trailing Stops on 105,708 Trades" (Aug 9
2026, visited this iteration --
https://setup4alpha.substack.com/p/trailing-stop-vs-fixed-stop-tested):
source's own isolated-exit-testing methodology uses EXACT entry
`C > ma200 and C[1] <= ma200[1]` (a fresh SMA200 upcross, filled next
open) with a baseline exit `C < ma200` (SMA200 downcross), and then
layers various trailing stops UNDER that baseline exit, whichever
triggers first. Source's own disclosed free-tier finding (#6 of 8,
Classic Donchian Low): a trailing stop at the lowest LOW of the last
N days (anchored 1 day back) "beats the close version [lowest CLOSE] at
every lookback" by roughly +0.24% per trade vs the close-only channel's
weaker performance, though both add modestly on top of the SMA200
backstop exit.

This repo has extensively tested Donchian-breakout ENTRY + N-day-low
trailing-stop EXIT combinations (2026-09-03-008 etc.), but never this
specific construction: entry is a discrete SMA200 CROSSOVER EVENT (not a
Donchian high breakout), and the exit is the tighter of (SMA200
downcross) OR (Donchian N-day-low breach), matching the source's own
isolated-exit-comparison design. Tested on both equity and crypto per
this repo's standard grid.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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
    trend_sma_window: int = 200,
    donchian_low_window: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: fresh SMA(trend_sma_window) upcross -- close crosses from at/
    below the SMA to strictly above it (discrete crossover EVENT, not a
    continuous "close > SMA" condition).

    Exit: whichever fires first -- (a) close crosses back below
    SMA(trend_sma_window) (source's own baseline exit), OR (b) close
    breaches the rolling low of the last donchian_low_window days,
    anchored one day back (source's own disclosed #6-ranked trailing
    stop, "Classic Donchian Low").
    """
    df = _prep(price_df)
    close = df["close"]
    low = df["low"] if "low" in df.columns else close

    sma = close.rolling(trend_sma_window).mean()
    above_sma = close > sma
    entry_signal = above_sma & (~above_sma.shift(1).fillna(False))

    exit_sma = close < sma
    donchian_low = low.rolling(donchian_low_window).min().shift(1)
    exit_donchian = close < donchian_low
    exit_signal = exit_sma | exit_donchian

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_position = True
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
