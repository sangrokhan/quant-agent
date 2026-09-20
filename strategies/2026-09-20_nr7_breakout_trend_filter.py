"""Strategy: NR7 (Narrow Range 7) breakout with trend-SMA filter, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per Google SERP corroboration this iteration (Quantified Strategies,
StockCharts, ForexTrainingGroup, Scribd, TusharBhumkar Institute -- browser_exec
used throughout, web_search DDGS backend TLS-connection-errored on every
query): the NR7 pattern, popularized by Toby Crabel ("Day Trading With
Short-Term Price Patterns And Opening Range Breakout"), flags the bar whose
high-low range is the NARROWEST of the last 7 bars (inclusive) as a
volatility-contraction signal. The disclosed trading rule (ForexTrainingGroup,
Scribd's "buying rules of the NR7 pattern"): place a buy-stop a small amount
above the NR7 bar's high; ForexTrainingGroup additionally requires price to
be above a long SMA (89-period, their disclosed trend filter) at breakout
for a long entry. Economic rationale (repeated across every source): volatility
is mean-reverting -- consolidation (narrow range) periods precede volatility
expansion, and a breakout out of the narrowest-range bar in the lookback
window, filtered by trend direction, aims to catch the start of that
expansion in the trend's direction.

Distinct from every other breakout strategy already in this repo: existing
breakout strategies (Donchian, 52-week-high, ATR-channel, etc.) key off a
ROLLING EXTREME price level; NR7 instead keys off a ROLLING-MINIMUM RANGE
bar (a volatility-contraction signal, using the narrow bar's own high, not
a broader rolling high) combined with a specific single-bar identification
rule. 0 prior NR7/narrow-range-bar entries in this repo.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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
    lookback: int = 7,
    breakout_buffer_pct: float = 0.001,
    trend_sma: int = 89,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    NR7 bar: the bar whose (high-low) range is the smallest of the trailing
    `lookback` bars (inclusive of itself).
    Long entry: the NEXT bar's high breaks above the NR7 bar's high plus a
    small buffer (breakout_buffer_pct), AND close is above its trend_sma
    (ForexTrainingGroup's disclosed directional filter, using close vs SMA
    as a proxy for the source's "price above the 89-period SMA at
    breakout" rule since intraday buy-stop fills aren't modeled here).
    Exit: after `max_hold_days` bars (source doesn't disclose an explicit
    exit rule beyond the initial breakout entry; a modest time-stop avoids
    holding indefinitely on a pattern with no disclosed exit signal).
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    rng = (high - low).abs()
    is_nr7 = rng == rng.rolling(lookback).min()
    sma = close.rolling(trend_sma).mean()
    above_trend = close > sma

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    nr7_high = None
    hold_remaining = 0

    high_vals = high.values
    is_nr7_vals = is_nr7.values
    above_trend_vals = above_trend.values

    for i in range(n):
        if hold_remaining > 0:
            position.iloc[i] = 1
            hold_remaining -= 1
            # Track NR7 high for a potential fresh entry check next bar too.
            if bool(is_nr7_vals[i]):
                nr7_high = high_vals[i]
            continue

        # Check breakout of the most recently flagged NR7 bar's high.
        if nr7_high is not None and high_vals[i] > nr7_high * (1 + breakout_buffer_pct) and bool(above_trend_vals[i]):
            position.iloc[i] = 1
            hold_remaining = max_hold_days - 1
            nr7_high = None
        else:
            position.iloc[i] = 0

        if bool(is_nr7_vals[i]):
            nr7_high = high_vals[i]

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
