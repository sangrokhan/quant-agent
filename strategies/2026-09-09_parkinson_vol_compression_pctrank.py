"""Strategy: Parkinson Volatility Compression Percentile-Rank Mean Reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Direct follow-up to this cron trigger's own near-miss/rejected candidate
2026-09-09-027 (Parkinson vol expansion-cross + trend filter, decisively
rejected -- too rare a joint condition, only 6-11 trades over 7.7yr). That
entry's own notes suggested trying the oscillator's percentile-rank form
instead of the EMA-signal-line expansion-cross. Per the same TradingView
"Parkinson Range Oscillator [BackQuant]" source read last iteration, the
script also computes:
    pctRank = PERCENTRANK(parkVol, pctrank_lookback)
where pctRank near 0 means volatility is at a historic low (extreme
compression) for that lookback window. This iteration tests a completely
different construction from the expansion-cross trend-following idea:
low Parkinson-vol percentile rank (compression / historically quiet
range) is itself an entry trigger for a short-horizon long, on the
economic intuition that periods of unusually quiet/compressed range often
precede reversion of any recent price weakness once volatility normalizes
(mean-reversion-on-compression, not trend-following-on-expansion) --
distinct in construction (percentile-rank threshold vs EMA-cross) and
economic mechanism (mean reversion vs trend continuation) from 2026-09-09-027.

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


def _parkinson_vol(df: pd.DataFrame, park_window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    log_hl2 = (np.log(high / low)) ** 2
    park_var = log_hl2.rolling(park_window).mean() / (4 * np.log(2))
    return np.sqrt(park_var) * 100


def _pctrank(series: pd.Series, lookback: int) -> pd.Series:
    def rank_fn(window: np.ndarray) -> float:
        if len(window) < 2:
            return np.nan
        last = window[-1]
        return float((window < last).sum()) / (len(window) - 1) * 100.0

    return series.rolling(lookback).apply(rank_fn, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    park_window: int = 10,
    pctrank_lookback: int = 100,
    compression_pctrank: float = 15.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Long/flat {0,1} position: long entry when Parkinson-vol percentile
    rank drops at/below compression_pctrank (historically quiet range);
    exit after max_hold_days (time-stop, no trend/level exit condition
    since this is a pure vol-regime timing signal, not a price-level
    mean-reversion trigger)."""
    df = _prep(price_df)
    close = df["close"]
    park_vol = _parkinson_vol(df, park_window)
    pctrank = _pctrank(park_vol, pctrank_lookback)

    entry = pctrank <= compression_pctrank

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0
    for i in range(len(df)):
        if in_position:
            hold_count += 1
            if hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]) if not pd.isna(entry.iloc[i]) else False:
                in_position = True
                hold_count = 0
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
