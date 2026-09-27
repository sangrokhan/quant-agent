"""Strategy: 5-asset GTAA dual-momentum rotation with an IEF bond-proxy
fallback instead of cash when the absolute-momentum gate fails.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-041's own
"Future idea" note in its `notes` field):
The already-tested 2026-09-11-041 (GTAA 5-asset SPY/EFA/EEM/GLD/TLT
dual-momentum, absolute-momentum CASH gate) was REJECTED but was a
near-miss improvement over its rejected predecessor: it fixed the MDD
breach entirely and roughly tripled Sharpe, but pass_fraction was still
only 0.139 (10/72 grid cells), entirely concentrated in the low-vol/equity
slice. That entry's own notes explicitly flagged as a follow-up: "try IEF
bond-proxy fallback instead of cash when absolute momentum negative,
mirroring accepted GEM/IEF dual-momentum (2026-09-07-023)" -- which itself
demonstrated (2026-09-07-022 vs -023) that a genuine income-bearing bond
safe-haven (IEF, 7-10yr Treasuries) meaningfully outperforms a flat 0%-cash
parking spot during risk-off regimes, because it earns carry instead of
sitting idle. This iteration implements exactly that fix: same
Quantpedia "Active Dual Momentum GTAA Strategy" (22 May 2026,
https://quantpedia.com/active-dual-momentum-gtaa-strategy/) methodology
(relative-momentum ranking across a diversified basket + absolute-momentum
safeguard), but when the primary asset fails the absolute-momentum gate
(or isn't the top pick), the strategy holds IEF instead of cash, so return
contribution during risk-off periods is IEF's own return stream rather
than a flat 0.

Basket: SPY/EFA/EEM/GLD/TLT (same as 2026-09-11-041 for direct
comparability), momentum measured via trailing lookback_days rate-of-change
(RoC), re-ranked every rebalance_days trading days.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position,
        1 = primary asset held, 0 = IEF fallback held -- the position
        series alone doesn't capture the IEF leg's contribution, so
        generate_returns computes the blended return stream directly
        rather than deriving it from generate_signals * price_df's own
        returns.)

Note: generate_signals/generate_returns fetch the basket ETFs AND IEF
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
FALLBACK_SYMBOL = "IEF"

_basket_cache: dict = {}
_fallback_cache: dict = {}


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


def _load_fallback_returns(index: pd.DatetimeIndex) -> pd.Series:
    """Load IEF daily returns, reindexed/forward-filled to the primary
    asset's index. Cached across calls within a process."""
    cache_key = "ief"
    if cache_key in _fallback_cache:
        rets = _fallback_cache[cache_key]
    else:
        from loaders import load_equity

        start = index.min().to_pydatetime() if len(index) else datetime(2015, 1, 1)
        end = index.max().to_pydatetime() if len(index) else datetime(2026, 9, 1)
        pad_start = datetime(max(start.year - 2, 2005), 1, 1)

        df = _prep(load_equity(FALLBACK_SYMBOL, pad_start, end))
        rets = df["close"].pct_change().fillna(0.0)
        _fallback_cache[cache_key] = rets

    return rets.reindex(index, method="ffill").fillna(0.0)


def _regime_gate(
    price_df: pd.DataFrame,
    lookback_days: int = 126,
    rebalance_days: int = 5,
    primary_symbol: str = "SPY",
) -> pd.Series:
    """Return a boolean Series: True on days the primary asset should be
    held (top-ranked in basket AND its own trailing RoC positive)."""
    df = _prep(price_df)
    index = df.index
    basket_closes = _load_basket_closes(index)

    trailing_roc = basket_closes.pct_change(lookback_days)

    n = len(trailing_roc)
    rebalance_positions = list(range(0, n, max(rebalance_days, 1)))
    rebalance_dates = trailing_roc.index[rebalance_positions]

    rebalance_rows = trailing_roc.iloc[rebalance_positions]
    valid_mask = rebalance_rows.notna().all(axis=1)
    winner_at_rebalance = rebalance_rows[valid_mask].idxmax(axis=1)
    winner_at_rebalance.index = rebalance_dates[valid_mask.values]

    primary_roc_at_rebalance = rebalance_rows[primary_symbol][valid_mask]
    primary_positive_at_rebalance = (primary_roc_at_rebalance > 0)
    primary_positive_at_rebalance.index = rebalance_dates[valid_mask.values]

    winner_series = winner_at_rebalance.reindex(index, method="ffill")
    abs_mom_gate = primary_positive_at_rebalance.reindex(index, method="ffill").fillna(False)

    is_primary_top = (winner_series == primary_symbol)
    return (is_primary_top.fillna(False) & abs_mom_gate)


def generate_signals(
    price_df: pd.DataFrame,
    lookback_days: int = 126,
    rebalance_days: int = 5,
    primary_symbol: str = "SPY",
) -> pd.Series:
    """Return a {0,1} position series (1 = primary asset held, 0 = IEF
    fallback held instead of cash)."""
    hold_primary = _regime_gate(price_df, lookback_days, rebalance_days, primary_symbol)
    return hold_primary.astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    lookback_days: int = 126,
    rebalance_days: int = 5,
    primary_symbol: str = "SPY",
) -> pd.Series:
    """Blended daily returns: primary asset's return when the dual-momentum
    gate says hold it, IEF's return otherwise (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    index = close.index

    hold_primary = _regime_gate(price_df, lookback_days, rebalance_days, primary_symbol)
    primary_daily_ret = close.pct_change().fillna(0.0)
    fallback_daily_ret = _load_fallback_returns(index)

    # Shift the gate by 1 day: yesterday's decision determines today's
    # return exposure (avoid look-ahead bias).
    hold_primary_shifted = hold_primary.shift(1).fillna(False)

    strategy_ret = hold_primary_shifted.astype(float) * primary_daily_ret + \
        (~hold_primary_shifted).astype(float) * fallback_daily_ret
    return strategy_ret
