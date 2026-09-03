"""Strategy: Choppiness Index (CHOP) trending-regime gate + SMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-059):
Per QuantifiedStrategies' Choppiness Index article (Bill Dreiss): the
Choppiness Index is a non-directional 0-100 regime classifier -- low
values (<38) indicate a trending market, high values (>62) indicate a
choppy/ranging market. It is distinct from every prior volatility/trend
measure in this repo since it is purely a regime classifier, not a
directional oscillator or moving average. The specific exact
entry/exit rule from the source is paywalled; this implements a
mechanically-testable regime-gated trend filter: only take a long
position when CHOP signals a trending regime (below the trending
threshold) AND price confirms direction (close above a trend SMA), since
CHOP itself cannot indicate direction (source's own repeated caveat).

CHOP formula (standard, Bill Dreiss):
    TR = true range (max(H-L, |H-prev_close|, |L-prev_close|))
    CHOP = 100 * log10(sum(TR, n) / (max(High, n) - min(Low, n))) / log10(n)

Rule: long entry when CHOP(chop_window) < trending_threshold AND
close > SMA(trend_window); exit when CHOP > choppy_threshold OR the
trend filter breaks (close <= SMA(trend_window)).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
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


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _choppiness_index(df: pd.DataFrame, window: int) -> pd.Series:
    tr = _true_range(df)
    tr_sum = tr.rolling(window).sum()
    hh = df["high"].rolling(window).max()
    ll = df["low"].rolling(window).min()
    rng = (hh - ll).replace(0, np.nan)
    chop = 100.0 * np.log10(tr_sum / rng) / np.log10(window)
    return chop


def generate_signals(
    price_df: pd.DataFrame,
    chop_window: int = 14,
    trending_threshold: float = 38.0,
    choppy_threshold: float = 62.0,
    trend_window: int = 50,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    chop = _choppiness_index(df, window=chop_window)
    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    entry_signal = (chop < trending_threshold) & uptrend
    exit_signal = (chop > choppy_threshold) | (~uptrend)

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
