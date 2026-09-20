"""Strategy: 3-way monthly momentum rotation (SPY/TLT/EEM basket), adapted
to this repo's single-primary-asset interface: long the PRIMARY asset only
during months where its own trailing momentum ranks highest among a fixed
3-asset basket {primary, TLT, EEM}.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-139):
Per QuantifiedStrategies' "ETF Rotation Strategy for High Returns"
(https://www.quantifiedstrategies.com/etf-rotation-strategy/, visited via
browser_exec this iteration): rank SPY, TLT (20yr Treasury), and EEM
(MSCI Emerging Markets) monthly by trailing lookback return, hold ONLY the
single best performer for the following month, rebalanced every month-end.
Source's own backtest (2003-2026, no costs): 1-month lookback gives CAGR
9.4%, MaxDD 44% (broke down badly in 2022); 3-month lookback gives CAGR
11.5%, MaxDD 32% (materially more robust) -- both improve over plain
buy-and-hold SPY's much higher published drawdown. This repo's
generate_signals/generate_returns interface takes a single primary
price_df, so this is adapted as: go LONG the primary asset (price_df) only
in months where the primary's own trailing momentum is strictly the
highest of the 3-asset basket {primary, TLT, EEM}; flat otherwise (a
"rotate into me or stay out" gate on the primary, rather than literally
rotating capital between all three legs, since the interface can only
return a position series for the primary). Distinct from all prior
2-asset GEM/dual-momentum constructions in this repo (2026-09-04-097,
2026-09-07-022/023, which use an absolute-momentum-gated 2-asset SAFE-HAVEN
switch) -- this is a 3-asset RELATIVE-STRENGTH ranking with no safe-haven
concept, following the source's exact "rank and hold the single winner"
methodology.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_companion(symbol: str, start, end) -> pd.Series:
    df = _prep(load_equity(symbol, start, end))
    return df["close"]


def _month_end_mask(index: pd.DatetimeIndex) -> pd.Series:
    periods = index.to_period("M")
    is_month_end = pd.Series(False, index=index)
    for i in range(len(index) - 1):
        if periods[i] != periods[i + 1]:
            is_month_end.iloc[i] = True
    if len(index) > 0:
        is_month_end.iloc[-1] = True
    return is_month_end


def _simulate(
    price_df: pd.DataFrame,
    companion_symbols=("TLT", "EEM"),
    lookback_days: int = 63,
) -> pd.DataFrame:
    df = _prep(price_df)
    primary_close = df["close"]
    start, end = primary_close.index.min(), primary_close.index.max()
    if getattr(start, "tzinfo", None) is not None:
        start = start.tz_localize(None)
    if getattr(end, "tzinfo", None) is not None:
        end = end.tz_localize(None)

    companions = {}
    for sym in companion_symbols:
        c = _load_companion(sym, start, end)
        companions[sym] = c.reindex(primary_close.index, method="ffill")

    primary_trail = primary_close.pct_change(lookback_days)
    companion_trail = {sym: c.pct_change(lookback_days) for sym, c in companions.items()}

    is_month_end = _month_end_mask(primary_close.index)
    primary_daily_ret = primary_close.pct_change().fillna(0.0)

    holding_primary = pd.Series(False, index=primary_close.index)
    current = False
    for i in range(len(primary_close)):
        if is_month_end.iloc[i]:
            p_ret = primary_trail.iloc[i]
            c_rets = [companion_trail[sym].iloc[i] for sym in companion_symbols]
            if pd.notna(p_ret) and all(pd.notna(r) for r in c_rets):
                current = p_ret > max(c_rets)
        holding_primary.iloc[i] = current

    holding_applied = holding_primary.shift(1).fillna(False)

    strat_ret = pd.Series(0.0, index=primary_close.index)
    strat_ret[holding_applied] = primary_daily_ret[holding_applied]

    position = holding_applied.astype(int)
    return pd.DataFrame({"position": position, "returns": strat_ret}, index=primary_close.index)


def generate_signals(
    price_df: pd.DataFrame,
    lookback_days: int = 63,
) -> pd.Series:
    result = _simulate(price_df, lookback_days=lookback_days)
    return result["position"]


def generate_returns(
    price_df: pd.DataFrame,
    lookback_days: int = 63,
) -> pd.Series:
    result = _simulate(price_df, lookback_days=lookback_days)
    return result["returns"]
