"""Strategy: Lumber/Gold ratio (Gayed RORO indicator) risk-on regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-059):
Per quantifiedstrategies.com's "Lumber/Gold Ratio Trading Strategy For
Stocks And Bonds" article, Michael Gayed created the lumber/gold ratio
(WOOD/GLD as ETF proxies) as a Risk-On/Risk-Off (RORO) indicator: lumber is
a cyclical/economic-growth proxy (housing & construction demand), gold is
a non-cyclical safe-haven/store-of-value asset with low correlation to
equities and macro variables. The article's own modified/simplified rule
(as opposed to Gayed's original 13-week-momentum comparison): when the
WOOD/GLD ratio is higher than it was `lookback_days` ago, take a risk-on
stance (long the traded equity asset); when lower, go flat/defensive
(their own backtest rotates into TLT bonds instead, but this repo's
generate_signals/generate_returns contract operates on a single traded
asset's price_df, so the "defensive" leg here is simply flat rather than a
second long position in TLT -- long-only single-asset adaptation).

This is the first Gayed-style intermarket RORO ratio strategy in this
repo -- distinct from the already-tested SPY/TLT (2026-09-05-036, direct
stock-vs-bond ratio) and gold/silver, copper/gold, HYG/LQD, yield-curve,
DXY, MOVE-index regime filters: lumber/gold specifically encodes a
housing-cycle/economic-growth-vs-safe-haven signal, not a pure
stock-vs-bond or credit-market signal.

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
    """Fetch WOOD/GLD close ratio series covering [start, end], cached."""
    key = (start.date().isoformat(), end.date().isoformat())
    if key in _ratio_cache:
        return _ratio_cache[key]

    fetch_start = datetime(max(start.year - 2, 2000), 1, 1, tzinfo=timezone.utc)
    fetch_end = datetime(end.year + 1, 1, 1, tzinfo=timezone.utc)

    wood = load_equity("WOOD", fetch_start, fetch_end)
    gld = load_equity("GLD", fetch_start, fetch_end)

    wood = wood.set_index(pd.to_datetime(wood["timestamp"], utc=True))["close"]
    gld = gld.set_index(pd.to_datetime(gld["timestamp"], utc=True))["close"]

    ratio = (wood / gld).dropna()
    ratio = ratio[~ratio.index.duplicated(keep="first")].sort_index()
    _ratio_cache[key] = ratio
    return ratio


def generate_signals(
    price_df: pd.DataFrame,
    lookback_days: int = 21,
) -> pd.Series:
    """Return a {0,1} long/flat position series from the WOOD/GLD ratio momentum.

    Long (risk-on) when today's ratio > ratio `lookback_days` trading days
    ago (~1 month per the source's "higher than the month before" rule);
    flat (risk-off) otherwise.
    """
    df = _prep(price_df)
    idx = df.index

    ratio_full = _get_ratio(idx.min(), idx.max())
    ratio = ratio_full.reindex(idx, method="ffill").bfill()

    ratio_prior = ratio.shift(lookback_days)
    position = (ratio > ratio_prior).fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
