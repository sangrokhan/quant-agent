"""Strategy: Standalone VIX-below-own-SMA calm-regime gate on SMA trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-040):
Per SetupAlpha's "I Tested 12 'Smart Money' Regime Filters" (Part 3,
2026-06-28, visited this iteration -- https://setupalpha.substack.com/p/i-tested-12-smart-money-regime-filters):
rank #8 of 12 is `Regime: VIX close < VIX's own rolling SMA(vixMaLen)` --
stay long while implied-volatility fear is falling/calm relative to its
own recent trend. Source's own disclosed finding: best COVID-crash score
of all 45 filters in the 3-part series (97% of the COVID crash dodged),
but costs ~3 points/year since the VIX spikes often without a genuine
crash following (0.71x holding overall).

This repo's existing VIX<own-SMA use (2026-09-08-153, "Overnight-Return
Premium, Trend + VIX-Calm-Regime Gate") combines this VIX condition with
TWO other conditions (a 20d MA trend filter AND a proprietary "Brain
Market Sentiment" indicator not reproducible here) as an overnight-return
strategy. This strategy tests the VIX<own-SMA condition standalone, as
the ONLY gate on a plain close>SMA(trend_sma_window) daily trend-following
signal (no proprietary sentiment component, no overnight-only return
construction) -- a materially simpler, first-time-isolated test of this
exact regime-filter rule in this repo.

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

_vix_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_vix_calm_gate(index: pd.DatetimeIndex, vix_sma_window: int) -> pd.Series:
    """Load ^VIX close, compute VIX < its own rolling SMA gate, reindexed
    to match the primary asset's index. Cached across calls within a
    process."""
    cache_key = vix_sma_window
    if cache_key in _vix_cache:
        gate = _vix_cache[cache_key]
    else:
        from loaders import load_equity

        start = index.min().to_pydatetime() if len(index) else datetime(2015, 1, 1)
        end = index.max().to_pydatetime() if len(index) else datetime(2026, 9, 1)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        pad_start = start.replace(year=max(start.year - 2, 2005))

        vix_df = _prep(load_equity("^VIX", pad_start, end))
        vix_close = vix_df["close"]
        vix_sma = vix_close.rolling(vix_sma_window).mean()
        gate = (vix_close < vix_sma).astype(int)
        _vix_cache[cache_key] = gate

    reindexed = gate.reindex(index, method="ffill").fillna(0).astype(int)
    return reindexed


def generate_signals(
    price_df: pd.DataFrame,
    trend_sma_window: int = 200,
    vix_sma_window: int = 50,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long when close > own trend_sma_window-day SMA AND VIX is below its
    own vix_sma_window-day SMA (calm-volatility-regime gate); flat
    otherwise.
    """
    df = _prep(price_df)
    close = df["close"]

    own_sma = close.rolling(trend_sma_window).mean()
    own_trend_up = close > own_sma

    vix_gate = _load_vix_calm_gate(df.index, vix_sma_window)

    position = (own_trend_up.astype(int) & vix_gate).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
