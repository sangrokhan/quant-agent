"""Strategy: GLD/TLT price-ratio regime gate on SPY/QQQ SMA trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-031):
Per Quantpedia's "Using Inflation Data for Systematic Gold and Treasury
Investment Strategies" (Cyril Dujava, Feb 2025, visited this iteration):
accelerating (month-over-month) inflation historically favors gold (GLD)
while decelerating inflation favors treasury bonds (IEF/TLT) -- the
source's own risk/return table shows "Inflation DOWN regime is highly
favorable for bonds, while accelerating inflation benefits gold". This
repo has no FRED/BLS point-in-time CPI data source (data/loaders.py only
exposes yfinance/ccxt OHLCV), so the exact 2-consecutive-month
acceleration/deceleration trigger cannot be reproduced. Instead, this
strategy proxies the SAME underlying gold-vs-bonds relative-performance
signal directly and continuously via the GLD/TLT PRICE RATIO: when the
ratio is rising relative to its own trailing SMA (gold outperforming
treasuries = inflation-up-like regime, per the source's own documented
asset performance table), that historically corresponds to a period when
raw treasury holding suffers -- so as an equity trend-following regime
gate we take the OPPOSITE reading: treat a FALLING/below-SMA GLD/TLT ratio
(bonds outperforming gold = disinflationary/growth-friendly regime, the
source's "Inflation DOWN" bucket) as the risk-on gate for equities, since
that regime historically also has lower rate-hike/inflation-shock risk
for equities. Gate: long the primary asset's own SMA(trend_sma_window)
trend-following signal only when GLD/TLT ratio is BELOW its own
ratio_sma_window-day SMA (disinflationary/bond-favorable regime); flat
otherwise.

Novelty vs existing repo entries: distinct from the already-tested GLD/SLV
ratio z-score strategy (2026-09-05-030, gold vs silver) and the
Copper/Gold ratio (2026-09-05-032, 2026-09-10-039, industrial-growth
signal) -- this is the first GLD/TLT (gold vs long treasury) ratio
strategy in this repo, and distinct from the already-rejected SPY/TLT
ratio (2026-09-05-036, stock-vs-bond leadership, not gold-vs-bond).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)

Note: generate_signals/generate_returns fetch GLD and TLT data internally
via data/loaders.py (cache-first) since the grid-test harness only passes
the primary asset's price_df -- the GLD/TLT ratio is a fixed macro regime
input, not itself under test across asset classes.
"""

from __future__ import annotations

import sys
import os
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


_ratio_cache: dict = {}


def _load_gld_tlt_gate(index: pd.DatetimeIndex, ratio_sma_window: int) -> pd.Series:
    """Load GLD and TLT close, compute the GLD/TLT ratio's own rolling SMA,
    reindexed/forward-filled to match the primary asset's index. Cached
    across calls within a process. Gate = 1 when ratio < its own SMA
    (disinflationary/bond-favorable regime -> risk-on for equities)."""
    cache_key = ratio_sma_window
    if cache_key in _ratio_cache:
        gate = _ratio_cache[cache_key]
    else:
        from loaders import load_equity

        start = index.min().to_pydatetime() if len(index) else datetime(2015, 1, 1)
        end = index.max().to_pydatetime() if len(index) else datetime(2026, 9, 1)
        pad_start = datetime(max(start.year - 2, 2005), 1, 1)

        gld_df = _prep(load_equity("GLD", pad_start, end))
        tlt_df = _prep(load_equity("TLT", pad_start, end))

        joined = pd.DataFrame({"gld": gld_df["close"], "tlt": tlt_df["close"]}).dropna()
        ratio = joined["gld"] / joined["tlt"]
        ratio_sma = ratio.rolling(ratio_sma_window).mean()
        gate = (ratio < ratio_sma).astype(int)
        _ratio_cache[cache_key] = gate

    reindexed = gate.reindex(index, method="ffill").fillna(0).astype(int)
    return reindexed


def generate_signals(
    price_df: pd.DataFrame,
    trend_sma_window: int = 200,
    ratio_sma_window: int = 100,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long when close > own trend_sma_window-day SMA AND GLD/TLT ratio is
    below its own ratio_sma_window-day SMA (disinflationary regime gate);
    flat otherwise.
    """
    df = _prep(price_df)
    close = df["close"]

    own_sma = close.rolling(trend_sma_window).mean()
    own_trend_up = close > own_sma

    ratio_gate = _load_gld_tlt_gate(df.index, ratio_sma_window)

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
