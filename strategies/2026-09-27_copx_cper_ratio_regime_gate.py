"""Strategy: COPX/CPER (copper miners vs copper commodity futures) ratio
regime gate on SMA trend-following.

Hypothesis (2026-09-27 KB entry, this iteration): per
https://finance.yahoo.com/markets/commodities/articles/copx-vs-cper-copper-miners-181745220.html
(Global X Copper Miners ETF COPX delivered 449% over 10yr vs United States
Copper Index Fund CPER's 160% over the same window; "COPX is a leveraged bet
on copper prices, filtered through mining company income statements...
miner margins expand faster than the underlying price because most costs
are fixed"), a rising COPX/CPER ratio (miners outperforming the commodity)
proxies elevated risk appetite for high-operating-leverage industrial-metal
equities, extending this repo's already-validated GDX/GLD, GDXJ/GDX, and
SILJ/SIL miner-vs-commodity ratio-regime-gate pattern (all accepted) to a
fourth, previously-untested metal pair: copper miners vs copper futures
(0 prior KB hits on COPX/CPER specifically). Same construction: long the
primary asset's own SMA-trend-following signal only when the COPX/CPER
ratio is above its own rolling SMA (risk-on proxy); flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

_ratio_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_copx_cper_gate(index: pd.DatetimeIndex, ratio_sma_window: int) -> pd.Series:
    """Load COPX and CPER closes, compute COPX/CPER ratio vs its own rolling
    SMA gate (True = ratio above SMA = copper miners outperforming copper
    futures = risk-on proxy), reindexed to match the primary asset's index."""
    cache_key = ratio_sma_window
    if cache_key in _ratio_cache:
        gate = _ratio_cache[cache_key]
    else:
        from loaders import load_equity

        start = index.min().to_pydatetime() if len(index) else datetime(2015, 1, 1)
        end = index.max().to_pydatetime() if len(index) else datetime(2026, 9, 1)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        pad_start = start.replace(year=max(start.year - 2, 2013))

        copx_close = _prep(load_equity("COPX", pad_start, end))["close"]
        cper_close = _prep(load_equity("CPER", pad_start, end))["close"]
        ratio = (copx_close / cper_close).dropna()
        ratio_sma = ratio.rolling(ratio_sma_window).mean()
        gate = (ratio > ratio_sma).astype(int)
        _ratio_cache[cache_key] = gate

    reindexed = gate.reindex(index, method="ffill").fillna(0).astype(int)
    return reindexed


def generate_signals(
    price_df: pd.DataFrame,
    trend_sma_window: int = 200,
    ratio_sma_window: int = 100,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long when close > own trend_sma_window-day SMA AND COPX/CPER ratio is
    above its own ratio_sma_window-day SMA (copper miners outperforming
    copper futures -- risk-on/high-beta-appetite proxy); flat otherwise.
    """
    df = _prep(price_df)
    close = df["close"]

    own_sma = close.rolling(trend_sma_window).mean()
    own_trend_up = close > own_sma

    ratio_gate = _load_copx_cper_gate(df.index, ratio_sma_window)

    position = (own_trend_up.astype(int) & ratio_gate).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    position = generate_signals(price_df, **kwargs)
    # shift position by 1 to avoid lookahead: today's return earned by
    # yesterday's end-of-day position
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
