"""Strategy: HYG/IEF credit-risk rotation (relative + absolute momentum,
monthly rebalance) -- always-invested switch between high-yield credit and
Treasuries.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-024):
Per an iM-Best "Bond Market Trader" blog post
(indexswingtrader.blogspot.com, 2019) summarizing a simplified fixed-income
rotation idea: "generally, when equity returns are good, high yield bonds
outperform investment grade/Treasury bonds" -- so a relative-momentum
rotation between a high-yield credit ETF (HYG) and a Treasury ETF (IEF)
should capture risk-on/risk-off credit cycles without needing equity data
at all. The original post's exact model uses 6 undisclosed proprietary
stock-market timers plus a CAPE-based risk-premium threshold, which is not
reproducible; this strategy tests the simplified, fully disclosed core
mechanism only: hold whichever of {HYG, IEF} has the higher trailing
lookback_days return (relative momentum), with an absolute-momentum gate
(if HYG's own trailing return is negative, force IEF regardless of the
relative comparison) -- i.e. the exact same GEM (Gary Antonacci Dual
Momentum) mechanic already used for SPY-vs-IEF (2026-09-07-023, accepted)
and SPY-vs-TLT (2026-09-07-022, rejected), just applied to two BOND ETFs
instead of an equity-vs-bond pair. First bond-vs-bond (credit-vs-duration)
GEM rotation in this repo, distinct from the already-tested HYG/LQD
spread-LEVEL regime filter (2026-09-05-025, rejected) which used a fixed
Z-score threshold on the HYG/LQD ratio rather than relative momentum
between HYG and IEF specifically.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)

Note: price_df passed in is HYG (the "risk" leg here is credit risk, not
equity); IEF is fetched internally as the safe_haven_symbol companion.
Reuses the exact GEM simulation mechanics of
strategies/2026-09-07_gem_dual_momentum_spy_ief.py.
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


def _load_companion(companion_symbol: str, start, end) -> pd.Series:
    df = _prep(load_equity(companion_symbol, start, end))
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
    safe_haven_symbol: str = "IEF",
    lookback_days: int = 252,
) -> pd.DataFrame:
    """price_df is the RISK asset (SPY/QQQ); safe_haven_symbol (TLT) is
    fetched internally. Antonacci's GEM logic: hold whichever of
    {risk, safe_haven} has the higher trailing return, gated by the RISK
    asset's own absolute momentum (if risk momentum <=0, force safe_haven
    regardless of relative comparison -- true GEM behavior, distinct from
    2026-09-04-097's symmetric-gate variant which allowed 'cash' whenever
    EITHER leg's absolute momentum was non-positive)."""
    df = _prep(price_df)
    risk_close = df["close"]
    start, end = df.index.min(), df.index.max()
    if getattr(start, "tzinfo", None) is not None:
        start = start.tz_localize(None)
    if getattr(end, "tzinfo", None) is not None:
        end = end.tz_localize(None)
    safe_close = _load_companion(safe_haven_symbol, start, end)
    safe_close = safe_close.reindex(risk_close.index, method="ffill")

    risk_trail = risk_close.pct_change(lookback_days)
    safe_trail = safe_close.pct_change(lookback_days)

    is_month_end = _month_end_mask(risk_close.index)

    risk_daily_ret = risk_close.pct_change().fillna(0.0)
    safe_daily_ret = safe_close.pct_change().fillna(0.0)

    holding = pd.Series("safe", index=risk_close.index, dtype=object)
    current = "safe"
    for i in range(len(risk_close)):
        if is_month_end.iloc[i] and pd.notna(risk_trail.iloc[i]) and pd.notna(safe_trail.iloc[i]):
            r_ret, s_ret = risk_trail.iloc[i], safe_trail.iloc[i]
            if r_ret <= 0:
                current = "safe"  # absolute-momentum gate: risk asset losing -> bonds, always
            elif r_ret > s_ret:
                current = "risk"
            else:
                current = "safe"
        holding.iloc[i] = current

    holding_applied = holding.shift(1).fillna("safe")

    strat_ret = pd.Series(0.0, index=risk_close.index)
    strat_ret[holding_applied == "risk"] = risk_daily_ret[holding_applied == "risk"]
    strat_ret[holding_applied == "safe"] = safe_daily_ret[holding_applied == "safe"]

    # position=1 always (fully invested in either risk or safe leg, never
    # literal cash) -- reflects GEM's "always invested somewhere" design.
    position = pd.Series(1, index=risk_close.index, dtype=int)
    return pd.DataFrame({"position": position, "returns": strat_ret}, index=risk_close.index)


def generate_signals(
    price_df: pd.DataFrame,
    safe_haven_symbol: str = "IEF",
    lookback_days: int = 252,
) -> pd.Series:
    result = _simulate(price_df, safe_haven_symbol, lookback_days)
    return result["position"]


def generate_returns(
    price_df: pd.DataFrame,
    safe_haven_symbol: str = "IEF",
    lookback_days: int = 252,
) -> pd.Series:
    result = _simulate(price_df, safe_haven_symbol, lookback_days)
    return result["returns"]
