"""Strategy: GDX/GLD (gold miners vs gold bullion) ratio regime gate on SMA trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-049):
Per Investopedia's "Optimize Your Gold Miner ETF Portfolio with Technical
Analysis" and BullionVault's gold-news framing (Google SERP snippets,
visited this iteration): "The GDX/GLD ratio is utilized to confirm market
sentiment, indicating whether gold mining stocks outperform physical
gold. Junior miners are high beta plays..." Gold miners (GDX) are a
leveraged/high-beta play on gold prices AND overall equity-market risk
appetite (miners are still stocks, subject to broad equity-market
sentiment on top of the gold-price beta). GDX outperforming GLD (ratio
rising) may therefore proxy a broader risk-on tape (equity-market
appetite for leveraged/cyclical names), not just a gold-specific signal.

Note: CXO Advisory's own GLD-GDX PAIRS-TRADING study (cited in this
iteration's search, https://www.cxoadvisory.com, visited previously per
this repo's records) found "no reliable convergence patterns" for
GLD-GDX MEAN REVERSION -- but this strategy tests a fundamentally
different construction: the ratio as a TREND/momentum REGIME GATE on
QQQ/SPY equity trend-following (not a GLD-GDX pairs mean-reversion trade
itself), mirroring this repo's already-validated cross-asset ratio-gate
pattern (GLD/TLT, Copper/Gold, TLT/IEF, XLU/SPY, SOXX/QQQ) which is
architecturally distinct from pairs mean-reversion.

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


def _load_gdx_gld_gate(index: pd.DatetimeIndex, ratio_sma_window: int) -> pd.Series:
    """Load GDX and GLD closes, compute GDX/GLD ratio vs its own rolling
    SMA gate (True = ratio above SMA = miners outperforming gold = risk-on
    proxy), reindexed to match the primary asset's index. Cached across
    calls within a process."""
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
        pad_start = start.replace(year=max(start.year - 2, 2005))

        gdx_close = _prep(load_equity("GDX", pad_start, end))["close"]
        gld_close = _prep(load_equity("GLD", pad_start, end))["close"]
        ratio = (gdx_close / gld_close).dropna()
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

    Long when close > own trend_sma_window-day SMA AND GDX/GLD ratio is
    above its own ratio_sma_window-day SMA (gold miners outperforming
    gold bullion -- risk-on/high-beta-appetite proxy); flat otherwise.
    """
    df = _prep(price_df)
    close = df["close"]

    own_sma = close.rolling(trend_sma_window).mean()
    own_trend_up = close > own_sma

    ratio_gate = _load_gdx_gld_gate(df.index, ratio_sma_window)

    position = (own_trend_up.astype(int) & ratio_gate).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
