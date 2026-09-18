"""Strategy: VIX absolute-level hysteresis regime switch (buy on VIX>30, trim on VIX<15).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-009):
Per https://github.com/alimuqeem/vix-regime-switch-backtest (a from-scratch
independent 30-year 1996-2026 backtest, itself a reaction to a viral X/Twitter
"cheat code" rule by @NoLimitGains): buy the S&P 500 when VIX closes above 30
(panic/crash-level fear), and trim to cash (flat) when VIX closes back below
15 (calm/complacency level). This is a STATE-MACHINE / HYSTERESIS construction
-- once triggered long by VIX>30, the position is HELD through the recovery
regardless of subsequent VIX wiggles, only exiting when VIX later closes below
the much lower 15 threshold. This is structurally distinct from every prior
VIX strategy in this repo (all of which use a single threshold cross, a
ratio vs VIX3M/VIX9D term structure, or a rolling SMA/regime gate applied
EVERY bar) -- here the entry and exit thresholds are two different absolute
VIX levels with no re-evaluation in between, i.e. true two-level hysteresis.
The source's own reported result (SPY 1996-2026, next-day-open execution,
5bps cost): CAGR 7.20% vs 10.44% buy&hold, Sharpe 0.36 vs 0.49 buy&hold,
same max drawdown (-55.19%) as buy&hold, only ~50% of trading days invested,
9 round-trip trades, 100% trade-level win rate (small sample). The source's
OWN headline finding is this rule does NOT beat buy-and-hold on Sharpe or
total return over the full 30-year sample -- but the goal here is to test
it independently on this repo's own QQQ/SPY/BTC/ETH data and validator
suite (shorter ~2018-2026 window, different tie-breaking/cost assumptions),
since a rule failing on one long sample can still pass a different repo's
specific validator thresholds (Sharpe>=1.0 over ~8yr, not 30yr CAGR-vs-B&H).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

_vix_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_vix_close(index: pd.DatetimeIndex) -> pd.Series:
    """Load ^VIX close, reindexed/ffilled to the primary asset's index.
    Cached across calls within a process."""
    if "vix" in _vix_cache:
        vix_close = _vix_cache["vix"]
    else:
        from loaders import load_equity

        start = index.min().to_pydatetime() if len(index) else datetime(2015, 1, 1)
        end = index.max().to_pydatetime() if len(index) else datetime(2026, 9, 1)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        pad_start = start.replace(year=max(start.year - 2, 2005))

        vix_df = _prep(load_equity("^VIX", pad_start, end))
        vix_close = vix_df["close"]
        _vix_cache["vix"] = vix_close

    reindexed = vix_close.reindex(index, method="ffill")
    return reindexed


def _hysteresis_state(vix: pd.Series, enter_level: float, exit_level: float) -> pd.Series:
    """Two-level hysteresis state machine: once VIX closes above enter_level,
    state flips to 1 (long) and STAYS 1 regardless of intermediate VIX values
    until VIX closes below exit_level, at which point state flips to 0 (flat)
    and stays 0 until VIX closes above enter_level again. No dependence on any
    other indicator (pure VIX absolute level, distinct from every prior VIX
    strategy in this repo)."""
    vix_arr = vix.to_numpy()
    n = len(vix_arr)
    state = np.zeros(n, dtype=int)
    cur = 0
    for i in range(n):
        v = vix_arr[i]
        if np.isnan(v):
            state[i] = cur
            continue
        if cur == 0 and v > enter_level:
            cur = 1
        elif cur == 1 and v < exit_level:
            cur = 0
        state[i] = cur
    return pd.Series(state, index=vix.index)


def generate_signals(
    price_df: pd.DataFrame,
    enter_level: float = 30.0,
    exit_level: float = 15.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long from the first VIX close > enter_level, held until VIX closes
    below exit_level (two-level hysteresis, no re-evaluation in between).
    """
    df = _prep(price_df)
    vix = _load_vix_close(df.index)
    position = _hysteresis_state(vix, enter_level, exit_level)
    position.index = df.index
    return position.astype(int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
