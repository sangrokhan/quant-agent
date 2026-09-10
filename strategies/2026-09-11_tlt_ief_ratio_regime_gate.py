"""Strategy: TLT/IEF (long-duration vs intermediate Treasury) ratio momentum regime gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-045):
Per ConvexTrade's TLT-vs-IEF comparison (Google SERP snippet, visited this
iteration -- "The duration ratio is the dominant driver of TLT-vs-IEF
performance. Curve-shape changes (steepening, flattening) produce
additional but smaller [effects]"): the TLT/IEF price ratio (long-
duration 20+yr Treasuries vs intermediate 7-10yr Treasuries) is
economically a duration-risk-appetite / yield-curve-shape proxy --
TLT outperforming IEF (ratio rising) reflects either falling long rates
faster than intermediate rates (bull flattening, "flight to duration"
during risk-off/recession-fear) or a bet on aggressive future rate cuts.

This repo has extensively tested other cross-asset ratio regime gates
(GLD/TLT, Copper/Gold, RSP/SPY, SOXX/QQQ, XLU/SPY, VVIX/VIX) using the
SAME validated construction pattern (gate a primary asset's own SMA
trend-following signal on whether a cross-asset ratio is above/below its
own trailing SMA), but never TLT/IEF specifically -- a genuinely new
bond-duration-ratio signal, distinct from the already-tested GLD/TLT
(gold-vs-bonds) and HYG/IEF (credit-vs-duration) ratios since this is a
pure DURATION-RISK ratio within the Treasury curve itself. Tested both
directions (ratio above its SMA = risk-off/flight-to-duration proxy,
gating flat; and the inverse, gating long) via the invert_signal param,
since the source doesn't give an unambiguous directional prediction for
equity/crypto trend-following.

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


def _load_tlt_ief_gate(index: pd.DatetimeIndex, ratio_sma_window: int, invert_signal: bool) -> pd.Series:
    """Load TLT and IEF closes, compute TLT/IEF ratio vs its own rolling
    SMA gate, reindexed to match the primary asset's index. Cached across
    calls within a process (cache key excludes invert_signal since that's
    applied after the cached lookup)."""
    cache_key = ratio_sma_window
    if cache_key in _ratio_cache:
        gate_raw = _ratio_cache[cache_key]
    else:
        from loaders import load_equity

        start = index.min().to_pydatetime() if len(index) else datetime(2015, 1, 1)
        end = index.max().to_pydatetime() if len(index) else datetime(2026, 9, 1)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        pad_start = start.replace(year=max(start.year - 2, 2005))

        tlt_close = _prep(load_equity("TLT", pad_start, end))["close"]
        ief_close = _prep(load_equity("IEF", pad_start, end))["close"]
        ratio = (tlt_close / ief_close).dropna()
        ratio_sma = ratio.rolling(ratio_sma_window).mean()
        # gate_raw = True means ratio is ABOVE its own SMA (TLT outperforming
        # IEF -- "flight to duration" / bull-flattening proxy)
        gate_raw = (ratio > ratio_sma)
        _ratio_cache[cache_key] = gate_raw

    reindexed = gate_raw.reindex(index, method="ffill").fillna(False)
    if invert_signal:
        return (~reindexed).astype(int)
    return reindexed.astype(int)


def generate_signals(
    price_df: pd.DataFrame,
    trend_sma_window: int = 200,
    ratio_sma_window: int = 100,
    invert_signal: bool = False,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long when close > own trend_sma_window-day SMA AND the TLT/IEF ratio
    regime condition holds (ratio above its own ratio_sma_window-day SMA
    by default, i.e. flight-to-duration/bull-flattening proxy; inverted
    if invert_signal=True). Flat otherwise.
    """
    df = _prep(price_df)
    close = df["close"]

    own_sma = close.rolling(trend_sma_window).mean()
    own_trend_up = close > own_sma

    ratio_gate = _load_tlt_ief_gate(df.index, ratio_sma_window, invert_signal)

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
