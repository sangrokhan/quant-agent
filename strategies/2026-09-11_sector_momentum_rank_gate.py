"""Strategy: Sector-Momentum-Rank Gate on trend-following (QuantPedia-style).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-118):
Per QuantPedia's "Sector Momentum - Rotational System" description ("Pick
3 ETFs with the strongest 12-month momentum into your portfolio and weight
them equally. Hold them for one month and then rebalance"), sector/asset
relative momentum ranking identifies which segments of the market are
currently leading. Rather than replicate the full rotational portfolio
(out of scope for this repo's single-asset generate_signals/returns
contract), this strategy adapts the ranking mechanism into a GATE: only
take the primary asset's own SMA-trend-following long signal when the
primary asset's own trailing momentum_window-day return ranks in the top
rank_threshold of a fixed reference basket (9 SPDR sector ETFs for equity
primaries: XLK/XLF/XLE/XLV/XLY/XLP/XLU/XLI/XLB; 5 major coins for crypto
primaries: BTC/ETH/SOL/BNB/XRP vs USDT) -- i.e. only trend-follow the
primary asset when IT is currently a momentum leader, not a laggard.
Distinct from every other sector-ratio-gate strategy already in this repo
(XLF/SPY, XLU/SPY, SOXX/QQQ, RSP/SPY, Copper/Gold, XLY/XLP -- all pairwise
two-asset ratios) because this uses a multi-asset RANK across a basket
rather than a single pairwise ratio, matching QuantPedia's actual
rotational-momentum construction more closely.

Source: https://quantpedia.com/strategies/sector-momentum-rotation-system/
(read via browser_exec fallback -- SERP snippet gave the mechanical rule
directly; web_search DDGS backend errored on all direct queries attempted
this cron trigger).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)

Note: price_df's own symbol identity isn't passed explicitly, so the gate
is keyed off matching price_df's own close series against each basket
member's close series (by value/index) is not reliable; instead we accept
an explicit `basket` param (list of loader symbols) and an `asset_class`
param so this module knows which loader + basket to use, and compare the
primary asset by RE-DERIVING its symbol implicitly is avoided: the grid
script passes `primary_symbol` explicitly per cell.
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

_basket_cache: dict = {}

EQUITY_BASKET = ["XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLU", "XLI", "XLB"]
CRYPTO_BASKET = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_rank_gate(
    index: pd.DatetimeIndex,
    primary_symbol: str,
    asset_class: str,
    momentum_window: int,
    rank_threshold: int,
) -> pd.Series:
    cache_key = (primary_symbol, asset_class, momentum_window, rank_threshold)
    if cache_key in _basket_cache:
        return _basket_cache[cache_key].reindex(index, method="ffill").fillna(0).astype(int)

    start = index.min().to_pydatetime() if len(index) else datetime(2015, 1, 1)
    end = index.max().to_pydatetime() if len(index) else datetime(2026, 9, 1)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    pad_start = start.replace(year=max(start.year - 2, 2005))

    basket = EQUITY_BASKET if asset_class == "equity" else CRYPTO_BASKET
    if primary_symbol not in basket:
        basket = basket + [primary_symbol]

    closes = {}
    if asset_class == "equity":
        from loaders import load_equity as _load

        for sym in basket:
            try:
                closes[sym] = _prep(_load(sym, pad_start, end))["close"]
            except Exception:
                continue
    else:
        from loaders import load_crypto as _load

        for sym in basket:
            try:
                closes[sym] = _prep(_load(sym, pad_start, end))["close"]
            except Exception:
                continue

    if primary_symbol not in closes or len(closes) < 2:
        gate = pd.Series(0, index=index)
        _basket_cache[cache_key] = gate
        return gate

    mom = pd.DataFrame({s: c.pct_change(momentum_window) for s, c in closes.items()})
    mom = mom.ffill()
    ranks = mom.rank(axis=1, ascending=False, method="first")
    primary_rank = ranks[primary_symbol]
    gate = (primary_rank <= rank_threshold).astype(int)
    gate = gate.reindex(sorted(set(gate.index)))
    _basket_cache[cache_key] = gate

    return gate.reindex(index, method="ffill").fillna(0).astype(int)


def generate_signals(
    price_df: pd.DataFrame,
    primary_symbol: str = "SPY",
    asset_class: str = "equity",
    trend_sma_window: int = 100,
    momentum_window: int = 252,
    rank_threshold: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long when close > own trend_sma_window-day SMA AND primary_symbol's own
    momentum_window-day momentum ranks in the top rank_threshold of its
    reference basket (momentum leadership gate).
    """
    df = _prep(price_df)
    close = df["close"]

    own_sma = close.rolling(trend_sma_window).mean()
    own_trend_up = close > own_sma

    rank_gate = _load_rank_gate(df.index, primary_symbol, asset_class, momentum_window, rank_threshold)

    position = (own_trend_up.astype(int) & rank_gate).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
