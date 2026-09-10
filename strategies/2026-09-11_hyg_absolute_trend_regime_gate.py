"""Strategy: HYG absolute-trend credit-spread regime gate on SPY/QQQ SMA
trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-027):
Per Google AI-overview synthesis of the "HYG Absolute Trend Rules" market
timing model (visited this iteration): HYG (iShares iBoxx $ High Yield
Corporate Bond ETF) price is a fast daily proxy for systemic credit-spread
risk appetite, since high-yield bonds are structurally senior to equities
but exposed to the same default/economic risk. The disclosed core rule:
HYG trading ABOVE its own 200-day SMA signals credit spreads are
contained/tightening (risk-on), while HYG BELOW its 200-day SMA signals
spreads are widening (risk-off, often leads equity stress).

This repo applies the rule as a regime GATE on a primary asset's (QQQ/SPY)
own SMA trend-following signal: long only when (a) the primary asset is
itself above its own trend SMA AND (b) HYG is above its own 200-day SMA
(credit conditions supportive); flat otherwise.

Novelty vs existing repo entries: distinct from the already-tested and
rejected HYG/LQD RATIO z-score regime filter (2026-09-05-025/-026, which
compares high-yield to investment-grade bond ETF prices) -- this strategy
uses HYG's own ABSOLUTE price trend vs its 200-day SMA, not a ratio against
another bond ETF, per the source's own disclosed "Standard Model" rule.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series

Note: generate_signals/generate_returns fetch HYG data internally via
data/loaders.py (cache-first) since the grid-test harness only passes the
primary asset's price_df -- HYG is a fixed macro regime input, not itself
under test across asset classes.
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


_hyg_cache: dict = {}


def _load_hyg_sma(index: pd.DatetimeIndex, hyg_sma_window: int) -> pd.Series:
    """Load HYG close, compute its rolling SMA, reindexed/forward-filled to
    match the primary asset's index. Cached across calls within a process."""
    cache_key = hyg_sma_window
    if cache_key in _hyg_cache:
        hyg_above_sma = _hyg_cache[cache_key]
    else:
        from loaders import load_equity

        start = index.min().to_pydatetime() if len(index) else datetime(2015, 1, 1)
        end = index.max().to_pydatetime() if len(index) else datetime(2026, 9, 1)
        # pad start earlier to have enough history for the SMA warmup
        pad_start = datetime(max(start.year - 2, 2005), 1, 1)
        hyg_df = load_equity("HYG", pad_start, end)
        hyg_df = _prep(hyg_df)
        hyg_close = hyg_df["close"]
        hyg_sma = hyg_close.rolling(hyg_sma_window).mean()
        hyg_above_sma = (hyg_close > hyg_sma).astype(int)
        _hyg_cache[cache_key] = hyg_above_sma

    reindexed = hyg_above_sma.reindex(index, method="ffill").fillna(0).astype(int)
    return reindexed


def generate_signals(
    price_df: pd.DataFrame,
    trend_sma_window: int = 200,
    hyg_sma_window: int = 50,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long when close > own trend_sma_window-day SMA AND HYG > its own
    hyg_sma_window-day SMA (credit-spread risk-on gate); flat otherwise.
    """
    df = _prep(price_df)
    close = df["close"]

    own_sma = close.rolling(trend_sma_window).mean()
    own_trend_up = close > own_sma

    hyg_gate = _load_hyg_sma(df.index, hyg_sma_window)

    position = (own_trend_up.astype(int) & hyg_gate).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
