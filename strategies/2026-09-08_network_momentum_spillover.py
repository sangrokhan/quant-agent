"""Strategy: Cross-Asset Momentum Spillover ("network momentum", single-edge

Hypothesis (see knowledge_base/strategies_log.jsonl, this id):
Per Pu/Roberts/Dong/Zohren "Network Momentum across Asset Classes" (2023,
Oxford-Man Institute), summarized at
https://www.quantitativo.com/p/network-momentum -- momentum propagates
through a graph connecting assets across classes, and the paper's own
ablation shows CROSS-CLASS links (bonds<->currencies<->commodities) are
"the secret sauce": restricting to a single asset class or intra-class
edges degrades performance relative to using inter-class neighbor momentum.

This repo's data/loaders.py has no futures/currency data, so we implement
the simplest possible single-edge analog of their mechanism rather than the
full 64-asset graph-learning pipeline: gate a PRIMARY equity/crypto asset's
position purely on a NEIGHBOR asset's own trailing momentum, where the
neighbor is deliberately chosen from a DIFFERENT class/segment than the
primary (equity primary -> bond-ETF neighbor TLT; crypto primary -> a
large-cap "systemic" crypto neighbor BTC/USDT acting as the closest
available cross-segment proxy, since this repo's crypto loader has no
non-crypto instruments). Critically, the primary asset's OWN trailing
return is never used to form the signal -- this isolates the network/
spillover hypothesis (neighbor momentum predicts target's next return)
from ordinary time-series momentum, which is the paper's central novelty
claim ("only ~65% correlated with individual momentum... a genuinely new
signal").

This is distinct from every prior cross-asset-ratio/rotation strategy in
this repo (e.g. 2026-09-04-097 dual_momentum_rotation, 2026-09-05 XLU/SPY,
copper/gold, gold/silver, IWM/SPY, RSP/SPY, SPY/TLT ratio-regime filters):
those all compare/ratio TWO assets' prices or use the PRIMARY's own trend
as (part of) the gate. Here the primary's own price history plays no role
in signal generation at all -- pure momentum spillover from one asset onto
an economically-unrelated other, mirroring the paper's core mechanism.

Signal logic
------------
- Compute the neighbor asset's simple trailing return over `neighbor_lookback`
  trading days.
- Long the PRIMARY asset (position=1) whenever the neighbor's trailing
  return exceeds `neighbor_threshold`; flat (position=0) otherwise.
- Signal is lagged by 1 day (decision made on neighbor's close, applied the
  next trading day) to avoid lookahead.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import sys
import os

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity, load_crypto  # noqa: E402


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_neighbor(neighbor_symbol: str, asset_class: str, start, end) -> pd.Series:
    if asset_class == "crypto":
        df = load_crypto(neighbor_symbol, start, end, interval="1d")
    else:
        df = load_equity(neighbor_symbol, start, end)
    df = _prep(df)
    return df["close"]


def _simulate(
    price_df: pd.DataFrame,
    neighbor_symbol: str = "TLT",
    asset_class: str = "equity",
    neighbor_lookback: int = 20,
    neighbor_threshold: float = 0.0,
) -> pd.DataFrame:
    df = _prep(price_df)
    primary_close = df["close"]
    start, end = df.index.min(), df.index.max()
    if getattr(start, "tzinfo", None) is not None:
        start = start.tz_localize(None)
    if getattr(end, "tzinfo", None) is not None:
        end = end.tz_localize(None)

    neighbor_close = _load_neighbor(neighbor_symbol, asset_class, start, end)
    neighbor_close = neighbor_close.reindex(primary_close.index, method="ffill")

    neighbor_trail = neighbor_close.pct_change(neighbor_lookback)

    raw_signal = (neighbor_trail > neighbor_threshold).astype(int)
    # lag by 1 day: decision made on neighbor's close, applied next day
    position = raw_signal.shift(1).fillna(0).astype(int)

    primary_daily_ret = primary_close.pct_change().fillna(0.0)
    strat_ret = position * primary_daily_ret

    return pd.DataFrame({"position": position, "returns": strat_ret}, index=primary_close.index)


def generate_signals(
    price_df: pd.DataFrame,
    neighbor_symbol: str = "TLT",
    asset_class: str = "equity",
    neighbor_lookback: int = 20,
    neighbor_threshold: float = 0.0,
) -> pd.Series:
    result = _simulate(price_df, neighbor_symbol, asset_class, neighbor_lookback, neighbor_threshold)
    return result["position"]


def generate_returns(
    price_df: pd.DataFrame,
    neighbor_symbol: str = "TLT",
    asset_class: str = "equity",
    neighbor_lookback: int = 20,
    neighbor_threshold: float = 0.0,
) -> pd.Series:
    result = _simulate(price_df, neighbor_symbol, asset_class, neighbor_lookback, neighbor_threshold)
    return result["returns"]
