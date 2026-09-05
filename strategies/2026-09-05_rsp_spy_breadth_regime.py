"""Strategy: RSP/SPY equal-weight-vs-cap-weight ratio market-breadth regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-033):
The RSP/SPY ratio (Invesco S&P 500 Equal Weight ETF / SPDR S&P 500 cap-
weight ETF) is a market-breadth proxy: a RISING ratio means the average
S&P 500 constituent is keeping pace with (or beating) the mega-cap-
concentrated cap-weighted index -- broad participation, a healthier
("less fragile") bull market. A FALLING ratio means market gains are
concentrated in a handful of mega-caps while the median stock lags --
narrow leadership, historically flagged as a warning sign for the
sustainability of the rally (per market commentary found via web search,
e.g. "RSP/SPY Ratio Hits 5-Year Low, Warning Signs for Investors" --
LinkedIn/Paul Lange: "Breadth matters. Sustained bull markets typically
see this ratio rising, not falling. A narrow rally is a fragile one.").
This strategy operationalizes that as a trend-following regime filter on
the ratio ITSELF (its own SMA slope), not a fixed absolute level (since
the ratio has no natural mean-reverting equilibrium the way, e.g.,
VIX/VIX3M's 1.0 threshold does -- it can trend for years as sector
composition/concentration evolves).

Distinct from the gold/silver (2026-09-05-030, accepted) and copper/gold
(2026-09-05-032, near-miss rejected) ratio strategies in this repo, which
are both commodities-market cross-asset signals; this is the first
market-internals/breadth-based regime filter tested here.

Signal logic
------------
- ratio = close(RSP) / close(SPY).
- `sma_window`-day SMA of the ratio; long (risk-on) when ratio's SMA is
  rising over the trailing `slope_window` days (SMA today > SMA
  slope_window days ago) -- breadth improving/broad rally. Flat
  (risk-off) when the SMA is falling -- breadth deteriorating/narrow
  rally.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402

_ratio_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def _get_ratio(start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    """Fetch RSP/SPY close ratio series covering [start, end], cached."""
    key = (start.date().isoformat(), end.date().isoformat())
    if key in _ratio_cache:
        return _ratio_cache[key]

    fetch_start = datetime(max(start.year - 2, 2000), 1, 1, tzinfo=timezone.utc)
    fetch_end = datetime(end.year + 1, 1, 1, tzinfo=timezone.utc)

    rsp = load_equity("RSP", fetch_start, fetch_end)
    spy = load_equity("SPY", fetch_start, fetch_end)

    rsp = rsp.set_index(pd.to_datetime(rsp["timestamp"], utc=True))["close"]
    spy = spy.set_index(pd.to_datetime(spy["timestamp"], utc=True))["close"]

    ratio = (rsp / spy).dropna()
    ratio = ratio[~ratio.index.duplicated(keep="first")].sort_index()
    _ratio_cache[key] = ratio
    return ratio


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 20,
    slope_window: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series from the RSP/SPY breadth trend."""
    df = _prep(price_df)
    idx = df.index

    ratio_full = _get_ratio(idx.min(), idx.max())
    ratio = ratio_full.reindex(idx, method="ffill").bfill()

    sma = ratio.rolling(sma_window, min_periods=sma_window // 2).mean()
    sma_prior = sma.shift(slope_window)
    rising = (sma > sma_prior).fillna(False)

    position = rising.astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
