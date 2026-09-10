"""Strategy: 5-asset GTAA rotation with an absolute-momentum cash gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-041):
Direct fix attempt for near-miss/rejected 2026-09-11-037 (5-asset momentum
rotation gate SPY/EFA/EEM/GLD/TLT, single-asset adaptation) which was
decisively rejected (Sharpe 0.11-0.32, MDD breach 0.29-0.32 across
lookbacks) because it always held the top-ranked basket asset with no
cash/flat escape hatch -- during broad risk-off periods even the "best"
basket performer can be losing money outright.

Per Quantpedia's "Active Dual Momentum GTAA Strategy" (22 May 2026,
visited this iteration --
https://quantpedia.com/active-dual-momentum-gtaa-strategy/): the source's
own disclosed methodology is a weekly-rebalanced dual-momentum GTAA across
a diversified ETF universe (their universe: SHY/IEF/UUP/GLD/USO/SPY/EFA/
QQQ/EEM) using rate-of-change (RoC) momentum, that layers TWO conditions
on top of simple relative-momentum ranking: (1) relative momentum --
select from the top of the ranked pool, AND (2) an ABSOLUTE momentum
filter -- only actually hold an asset whose own trailing RoC is POSITIVE;
otherwise stay in cash. This absolute-momentum "safeguard" is exactly the
missing ingredient in 2026-09-11-037's rejected construction.

Adapted here to this repo's single-asset generate_signals/generate_returns
interface the same way 2026-09-11-037 did: internally load the basket
ETFs (SPY/EFA/EEM/GLD/TLT, same basket for direct comparability) via
data/loaders.py, rank all 5 by trailing lookback_days RoC at each
rebalance (approximated with a rebalance_days-day rebalance cadence --
weekly per the source's own methodology, rather than 037's monthly),
return position=1 for the primary asset (default SPY) only when it is
BOTH the top-ranked pick AND its own trailing RoC is positive; flat
(cash) otherwise.

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
    lookback_days: int = 126,
    rebalance_days: int = 5,
    primary_symbol: str = "SPY",
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    At each rebalance_days-day cadence (default 5 = weekly), rank the
    5-ETF basket (SPY/EFA/EEM/GLD/TLT) by trailing lookback_days
    rate-of-change (RoC). Long the primary asset (traded via price_df)
    only during periods when BOTH: (a) primary_symbol is the top-ranked
    pick in the basket, AND (b) primary_symbol's own trailing RoC is
    positive (absolute momentum gate -- source's own disclosed
    "safeguard during market downturns"); flat (cash) otherwise.
    """
    df = _prep(price_df)
    index = df.index
    basket_closes = _load_basket_closes(index)

    trailing_roc = basket_closes.pct_change(lookback_days)

    # Rebalance every `rebalance_days` trading days (weekly by default),
    # using row-position stride rather than calendar Wednesday-anchoring
    # (repo's loaders don't guarantee a specific weekday is always present).
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

    # Forward-fill both the winner decision and the absolute-momentum gate
    # to every day until the next rebalance.
    winner_series = winner_at_rebalance.reindex(index, method="ffill")
    abs_mom_gate = primary_positive_at_rebalance.reindex(index, method="ffill").fillna(False)

    is_primary_top = (winner_series == primary_symbol)
    position = (is_primary_top.fillna(False) & abs_mom_gate).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
