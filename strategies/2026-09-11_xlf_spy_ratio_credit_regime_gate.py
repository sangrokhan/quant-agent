"""Strategy: XLF/SPY (financials-vs-broad-market) ratio credit-regime gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-050):
Per Google AI-overview synthesis (DiviStock Chronicles / TradingView,
visited this iteration): "The Financial Select Sector SPDR Fund (XLF) to
SPDR S&P 500 ETF Trust (SPY) relative strength ratio (XLF/SPY) serves as
a classic equity market leading indicator for credit health, systemic
risk appetite, and macroeconomic cycle inflection points... When XLF/SPY
rises, financials are outperforming the broader S&P 500, indicating an
expansionary regime, steepening yield curves, or healthy credit
creation. When it breaks down, it often telegraphs tightening credit
conditions, counterparty stress, or an impending economic contraction
before headline indices react." Financials (banks/capital markets) are
uniquely balance-sheet-sensitive to credit conditions, making their
relative performance a plausible LEADING indicator distinct from every
other sector-leadership ratio already tested in this repo (SOXX/QQQ
semis, XLU/SPY defensive-beta, RSP/SPY breadth, XLY/XLP discretionary-vs-
staples, Copper/Gold industrial growth) -- none of which specifically
target bank/credit-sector leadership.

Gate: long primary asset's own SMA(trend_sma_window) trend-following
signal only when XLF/SPY ratio is above its own ratio_sma_window-day SMA
(financials outperforming, expansionary/credit-healthy regime); flat
otherwise.

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


def _load_xlf_spy_gate(index: pd.DatetimeIndex, ratio_sma_window: int) -> pd.Series:
    """Load XLF and SPY closes, compute XLF/SPY ratio vs its own rolling
    SMA gate (True = ratio above SMA = financials leading = expansionary/
    credit-healthy regime), reindexed to match the primary asset's index.
    Cached across calls within a process."""
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

        xlf_close = _prep(load_equity("XLF", pad_start, end))["close"]
        spy_close = _prep(load_equity("SPY", pad_start, end))["close"]
        ratio = (xlf_close / spy_close).dropna()
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

    Long when close > own trend_sma_window-day SMA AND XLF/SPY ratio is
    above its own ratio_sma_window-day SMA (financials leading -- credit-
    healthy/expansionary regime proxy); flat otherwise.
    """
    df = _prep(price_df)
    close = df["close"]

    own_sma = close.rolling(trend_sma_window).mean()
    own_trend_up = close > own_sma

    ratio_gate = _load_xlf_spy_gate(df.index, ratio_sma_window)

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
