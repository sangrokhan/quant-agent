"""Strategy: Factor-Sleeve Momentum-Rank Gate (MTUM/QUAL/IWD/IWM basket).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-XXX):
Per The Intrinsic Investor's "Factor & Sector Rotation: A Systematic
Parameter Optimisation" study
(https://theintrinsicinvestor.com/research/etf-factor-sector-rotation-strategy/),
a disclosed two-sleeve monthly ETF rotation backtest (60 parameter
combinations over Compustat/WRDS data, July 2014-March 2026) uses a
"Factor sleeve" of four style-factor ETFs (MTUM momentum, QUAL quality,
IWD value, IWM small-cap) ranked by trailing N-month total return each
month, allocating to the single top-ranked ETF, with a SPY-based
drawdown filter (several variants disclosed: 12m return, 10m SMA,
200d SMA, 1m/10m SMA, death cross) sending both sleeves to cash in
deteriorating regimes.

This repo's single-asset generate_signals/generate_returns interface
cannot replicate the full monthly-rotation two-sleeve portfolio, so we
adapt the FACTOR SLEEVE specifically into a momentum-RANK GATE (same
adaptation pattern already validated for the Sector sleeve in this repo,
2026-09-11-118, accepted): only take the primary asset's (e.g. QQQ/SPY)
own SMA-trend-following long signal when the primary asset's trailing
momentum_window-day return ranks in the top rank_threshold of the
FACTOR basket {MTUM, QUAL, IWD, IWM} (a materially different, smaller,
STYLE-based basket vs. the existing SECTOR-based 9-ETF basket) -- i.e.
only trend-follow the primary asset when it is currently a momentum
leader among style factors, not laggard. For crypto, reuses the same
5-major-coin basket as the existing sector-rank-gate strategy (no
separate style-factor analogue exists in crypto).

Source: https://theintrinsicinvestor.com/research/etf-factor-sector-rotation-strategy/
(browser_exec direct fetch; web_search DDGS/Yahoo backend TLS-errored on
one query this iteration, worked on another).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

_basket_cache: dict = {}

FACTOR_BASKET = ["MTUM", "QUAL", "IWD", "IWM"]
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

    basket = FACTOR_BASKET if asset_class == "equity" else CRYPTO_BASKET
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
    rank_threshold: int = 2,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long when close > own trend_sma_window-day SMA AND primary_symbol's own
    momentum_window-day momentum ranks in the top rank_threshold of the
    FACTOR-STYLE reference basket {MTUM, QUAL, IWD, IWM} (equity) or the
    5-major-coin basket (crypto).
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
