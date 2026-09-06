"""Strategy: Dual Momentum (GEM, Gary Antonacci) SPY vs IEF -- shorter-
duration bond-ETF safe-haven, ACCEPTED variant.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-023):
This is a direct follow-up to 2026-09-07-022 (same cron trigger, prior
iteration), which tested this identical GEM mechanic with TLT (20+ Year
Treasury) as the safe haven and found max drawdown got WORSE than a plain
cash safe-haven (2026-09-04-097) -- TLT's long duration made it fall
alongside equities during 2022's rate-hike cycle, defeating its purpose.
That report's notes flagged testing "a shorter-duration, less
rate-sensitive bond ETF (IEF/SHY)" as the next step. This file is that
follow-up: identical GEM logic (absolute momentum gate + relative
momentum comparison, monthly rebalance) with IEF (iShares 7-10 Year
Treasury Bond ETF, confirmed available via data/loaders.load_equity)
as the safe haven instead of TLT.

At SPY / lookback_days=252 / safe_haven_symbol=IEF, ALL validators pass:
Sharpe 1.046, MDD 22.0%, TC-survival net Sharpe 1.043 (5 trades over
7.7yr), parameter sensitivity 0.193. This is the first ACCEPTED strategy
in this cron trigger's run. QQQ does NOT pass at any tested lookback with
IEF (best QQQ config passes Sharpe but fails MDD 29.9%) -- the accept is
scoped to SPY only, consistent with GEM's original design being
specifically an S&P 500-vs-bond rotation.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)

Note: reuses the exact simulation mechanics of
strategies/2026-09-04_dual_momentum_rotation.py (same relative+absolute
momentum monthly-rebalance logic) -- this file exists as an independently
loggable knowledge-base entry testing the specific TLT-safe-haven
hypothesis flagged as a follow-up, not a code refactor.
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
