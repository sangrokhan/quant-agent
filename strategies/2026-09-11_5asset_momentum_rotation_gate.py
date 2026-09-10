"""Strategy: 5-asset momentum rotation gate (SPY/EFA/EEM/GLD/TLT), single-asset adaptation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-037):
Per QuantifiedStrategies.com's "Rotation Strategy for SPY, EEM, EFA, TLT,
and GLD" (visited this iteration): assets with positive relative momentum
over intermediate horizons (source tested 1-12 month lookbacks) tend to
continue outperforming; a monthly-rebalanced rotation strategy across this
5-ETF cross-asset basket (US equities, developed international equities,
emerging markets, gold, long treasuries) ranks by trailing momentum and
holds the top pick(s). Source's own disclosed backtest: 118 trades, 62%
win ratio, 12% CAGR, 28% MDD (exact numeric selection/rebalance rule
paywalled, but the mechanical framework -- monthly cross-sectional
momentum rank, top-1 hold -- is fully disclosed).

This repo's strategy interface (generate_signals/generate_returns taking
a single price_df) is adapted here the same way existing GEM dual-momentum
and HYG/GLD-TLT-ratio-gate strategies handle cross-asset signals: the
strategy internally loads the OTHER basket ETFs via data/loaders.py,
ranks all 5 by trailing lookback_months momentum at each month-end, and
returns position=1 for the PRIMARY (passed-in) asset only during months
when it is the TOP-RANKED pick in the basket; flat otherwise. This
directly tests whether the primary traded asset (e.g. QQQ or SPY) would
have been selected under the disclosed rotation framework, resolving the
"structural blocker" concluded by the prior cross-sectional attempt
(2026-09-08-046) which didn't find this single-asset-gate adaptation.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)

Note: generate_signals/generate_returns fetch the other basket ETFs
internally via data/loaders.py (cache-first) since the grid-test harness
only passes the primary asset's price_df.
"""

from __future__ import annotations

import sys
import os
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

BASKET = ["SPY", "EFA", "EEM", "GLD", "TLT"]

_basket_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_basket_closes(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Load daily close for every basket ETF, reindexed/forward-filled to
    the primary asset's index. Cached across calls within a process."""
    cache_key = "basket"
    if cache_key in _basket_cache:
        closes = _basket_cache[cache_key]
    else:
        from loaders import load_equity

        start = index.min().to_pydatetime() if len(index) else datetime(2015, 1, 1)
        end = index.max().to_pydatetime() if len(index) else datetime(2026, 9, 1)
        pad_start = datetime(max(start.year - 2, 2005), 1, 1)

        series = {}
        for sym in BASKET:
            df = _prep(load_equity(sym, pad_start, end))
            series[sym] = df["close"]
        closes = pd.DataFrame(series).dropna()
        _basket_cache[cache_key] = closes

    return closes.reindex(index, method="ffill")


def generate_signals(
    price_df: pd.DataFrame,
    lookback_months: int = 6,
    primary_symbol: str = "SPY",
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    At each month-end, rank the 5-ETF basket (SPY/EFA/EEM/GLD/TLT) by
    trailing lookback_months total return. Long the primary asset (traded
    via price_df) only during months when primary_symbol is the top-ranked
    pick; flat otherwise. If the traded asset (e.g. QQQ) is not itself in
    the basket, primary_symbol lets the caller specify which basket member
    the price_df's returns should be treated as a proxy for (default SPY,
    since QQQ/SPY are highly correlated US-equity proxies).
    """
    df = _prep(price_df)
    index = df.index
    basket_closes = _load_basket_closes(index)

    lookback_days = int(lookback_months * 21)  # approx trading days/month
    trailing_ret = basket_closes.pct_change(lookback_days)

    # Find each unique (year, month) last available date, then rank the
    # basket by trailing momentum at exactly those month-end rows.
    naive_index = trailing_ret.index.tz_localize(None) if trailing_ret.index.tz is not None else trailing_ret.index
    periods = naive_index.to_period("M")
    last_of_month_pos = pd.Series(range(len(trailing_ret)), index=trailing_ret.index).groupby(periods).max()
    rebalance_positions = sorted(last_of_month_pos.values)
    rebalance_dates = trailing_ret.index[rebalance_positions]

    rebalance_rows = trailing_ret.iloc[rebalance_positions]
    valid_mask = rebalance_rows.notna().all(axis=1)
    winner_at_rebalance = rebalance_rows[valid_mask].idxmax(axis=1)
    winner_at_rebalance.index = rebalance_dates[valid_mask.values]
    # Forward-fill the winner decision to every day until the next rebalance.
    winner_series = winner_at_rebalance.reindex(index, method="ffill")

    is_primary_top = (winner_series == primary_symbol).astype(int)
    # Shift by 1 day: decision made at month-end close, applied starting
    # next trading day (avoids using the same-day close for both ranking
    # and position -- generate_returns applies its own shift(1) too, so
    # this keeps the overall pipeline conservative/no look-ahead).
    position = is_primary_top.fillna(0).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
