"""Strategy: Protective Asset Allocation (PAA) graduated crash-protection
weight, single-asset adaptation (primary leg).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-XXX):
Per Wouter Keller & JW Keuning's "PAA: A Simple Momentum-based Alternative
to Term Deposits", summarized by Allocate Smartly
(https://allocatesmartly.com/protective-asset-allocation/, read via
browser_exec this iteration -- web_search DDGS/Yahoo backend TLS-errored on
every query attempted): on the last trading day of each month, compute a
momentum score MOM = (close / SMA(13 month-end closes)) - 1 for each of 12
global asset classes. Let n = count of assets with MOM > 0. If n <= 6,
allocate the ENTIRE portfolio to a "crash protection" asset (IEF); else
crash-protection weight CP% = (12-n)/6, and the remaining (1-CP%) of the
portfolio is split equally (1/6 each) among the 6 highest-MOM assets.

This is a GRADUATED (non-binary) crash-protection allocation rule, distinct
from this repo's existing Faber 3-asset equal-weight-if-qualifying rotation
(2026-09-11-078, binary per-asset in/out with equal split among however many
qualify, no crash-protection asset, no cross-sectional selection of a
best-6) and from cross-sectional rank-and-pick-the-top-1 GTAA strategies
already tested. Adapted to this repo's single-asset
generate_signals/generate_returns contract: the PRIMARY traded asset (e.g.
QQQ) is held with weight = (1 - CP%) / 6 whenever it is BOTH MOM-positive
AND ranked in the top 6 of the 12-asset universe by MOM score, and 0
otherwise -- this reproduces exactly the primary asset's own contribution
to the source's graduated PAA construction (rather than modeling the whole
12-asset portfolio, which is out of scope for this repo's single-symbol
contract).

Universe (12 assets, proxies matching the source's own end-notes list):
SPY, QQQ, IWM, VGK, EWJ, EEM, VNQ, DBC, GLD, HYG, LQD, TLT (crash-protection
asset IEF is NOT part of the traded universe here -- the strategy either
holds the primary asset at its graduated weight, or is flat/cash for the
rest, since modeling an actual IEF crash-protection leg is out of scope for
a single-symbol generate_returns_fn).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (weight in [0, 1/6])
"""

from __future__ import annotations

import os
import sys

import pandas as pd

UNIVERSE = ["SPY", "QQQ", "IWM", "VGK", "EWJ", "EEM", "VNQ", "DBC", "GLD", "HYG", "LQD", "TLT"]


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _monthly_mom(close: pd.Series, mom_months: int) -> pd.Series:
    idx = pd.to_datetime(close.index).tz_localize(None)
    close_reidx = close.copy()
    close_reidx.index = idx
    monthly = close_reidx.resample("ME").last().dropna()
    sma = monthly.rolling(mom_months).mean()
    mom = (monthly / sma) - 1.0
    return mom


def _load_universe_monthly_mom(index: pd.DatetimeIndex, mom_months: int, primary_symbol: str) -> pd.DataFrame:
    """Load each universe member (except primary, loaded separately by the
    caller) via data/loaders.py and compute month-end MOM scores aligned to
    a common monthly index."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    start = (index.min() - pd.Timedelta(days=mom_months * 32 + 60)).to_pydatetime()
    end = (index.max() + pd.Timedelta(days=10)).to_pydatetime()

    mom_by_symbol = {}
    for sym in UNIVERSE:
        if sym == primary_symbol:
            continue
        df = load_equity(sym, start, end)
        close = df.set_index("timestamp")["close"] if "timestamp" in df.columns else df["close"]
        mom_by_symbol[sym] = _monthly_mom(close, mom_months)
    return pd.DataFrame(mom_by_symbol)


def generate_signals(
    price_df: pd.DataFrame,
    mom_months: int = 13,
    n_select: int = 6,
    cp_denominator: int = 6,
    primary_symbol: str = "QQQ",
) -> pd.Series:
    """Return a [0, 1/n_select] continuous weight series for the primary
    asset (intended to be run with `primary_symbol`'s price_df)."""
    df = _prep(price_df)
    close = df["close"]

    primary_mom = _monthly_mom(close, mom_months)
    basket_mom = _load_universe_monthly_mom(close.index, mom_months, primary_symbol)

    # Align all series to the same monthly index (union, then reindex).
    all_mom = basket_mom.copy()
    all_mom[primary_symbol] = primary_mom
    all_mom = all_mom.dropna(how="all")

    total_universe = len(UNIVERSE)
    weight_monthly = pd.Series(0.0, index=all_mom.index)

    for dt in all_mom.index:
        row = all_mom.loc[dt].dropna()
        if row.empty or primary_symbol not in row.index:
            continue
        n_positive = int((row > 0).sum())
        if n_positive <= (total_universe - cp_denominator):
            cp_pct = 1.0
        else:
            cp_pct = max(0.0, (total_universe - n_positive) / cp_denominator)
        risk_pct = 1.0 - cp_pct
        if risk_pct <= 0:
            continue
        top_n = row.sort_values(ascending=False).head(n_select)
        if primary_symbol in top_n.index and top_n[primary_symbol] > 0:
            weight_monthly.loc[dt] = risk_pct / n_select

    # Shift by 1 month (decision at month-end m applies to month m+1), then
    # forward-fill to daily.
    weight_monthly.index = weight_monthly.index + pd.offsets.MonthEnd(0)
    weight_monthly_shifted = weight_monthly.shift(1).fillna(0.0)

    daily_index = pd.to_datetime(close.index).tz_localize(None)
    weight_daily = weight_monthly_shifted.reindex(daily_index, method="ffill").fillna(0.0)
    weight_daily.index = close.index
    return weight_daily


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Weight-scaled daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    weight = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = weight.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
