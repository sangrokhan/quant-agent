"""Strategy: Composite (multi-lookback averaged) Dual Momentum Rotation
between Gold (GLD) and Bitcoin ("Digital Gold"), with volatility-targeted
position sizing.

Source: Quantpedia "Dual Momentum Allocation Between Physical Gold and
Bitcoin (Digital Gold)" (R. Vojtko, C. Dujava, 6 May 2026),
https://quantpedia.com/dual-momentum-allocation-between-physical-gold-and-bitcoin-digital-gold/,
as critiqued/detailed by Aligrithm's "6.58 Dual Momentum Between Gold and
Bitcoin (Two Stores of Value)" (14 Aug 2026, visited this iteration),
https://aligrithm.com/dual-momentum-between-gold-and-bitcoin-two-stores-of-value/.

This repo already has 2026-09-13_gold_bitcoin_dual_momentum_voltarget.py
(2026-09-13-003, accepted), which implements the source's SINGLE-lookback
(default 8-week) Antonacci relative+absolute dual-momentum switch with a
20% vol-targeting overlay, MDD 23.1%.

Aligrithm's own reading of the source material makes explicit that the
source's headline LOW-RISK number (12.01%/yr, Sharpe 1.37, MDD -12.27%)
is NOT a single-lookback result -- it is a COMPOSITE that AVERAGES the
position (and hence return) of three independent single-lookback dual
momentum sub-strategies (4-week, 8-week, 12-week), each vol-capped at 20%
individually, before combining. This diversifies away idiosyncratic
single-lookback whipsaw (a single 8-week window can stay "positive deep
into a decline" per Aligrithm) and is source's own stated reason the
composite's MDD is roughly HALF the single-lookback MDD.

This is therefore a distinct, testable hypothesis from 2026-09-13-003:
composite-of-3-lookbacks vs single-lookback, with the explicit prediction
(from the source itself) that MDD should improve materially at a modest
Sharpe cost.

Interface contract (see validation/grid_test.py, validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1}, 1 whenever
        the composite has ANY nonzero net exposure to GLD or BTC)
    generate_returns(price_df, **params) -> pd.Series (daily strategy
        returns = simple average of the 3 sub-strategies' daily returns)

The primary asset (`price_df`) is expected to be GLD (or another equity
ticker used as the "gold-like" leg for cross-asset-class grid testing);
BTC/USDT is fetched internally via data/loaders.py.load_crypto (same
pattern as the sibling single-lookback strategy).
"""

from __future__ import annotations

import sys
import os

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_crypto  # noqa: E402


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_partner_close(partner_symbol: str, start, end) -> pd.Series:
    df = load_crypto(partner_symbol, start, end, interval="1d")
    df = _prep(df)
    return df["close"]


def _single_lookback_sim(
    gold_close: pd.Series,
    btc_close: pd.Series,
    lookback_weeks: int,
    vol_cap: float,
    vol_window_days: int,
    rebalance_weekday: int,
) -> pd.DataFrame:
    idx = gold_close.index
    lookback_days = lookback_weeks * 5

    gold_mom = gold_close.pct_change(lookback_days)
    btc_mom = btc_close.pct_change(lookback_days)

    gold_daily_ret = gold_close.pct_change().fillna(0.0)
    btc_daily_ret = btc_close.pct_change().fillna(0.0)

    gold_vol = gold_daily_ret.rolling(vol_window_days).std() * np.sqrt(252)
    btc_vol = btc_daily_ret.rolling(vol_window_days).std() * np.sqrt(252)

    is_rebalance_day = pd.Series(idx.weekday == rebalance_weekday, index=idx)

    long_btc = (btc_mom > gold_mom) & (btc_mom > 0)
    long_gold = (gold_mom > btc_mom) & (gold_mom > 0)

    holding_raw = pd.Series("cash", index=idx, dtype=object)
    holding_raw[long_btc.fillna(False)] = "btc"
    holding_raw[long_gold.fillna(False)] = "gold"

    btc_w = (vol_cap / btc_vol).clip(upper=1.0).fillna(0.0)
    gold_w = (vol_cap / gold_vol).clip(upper=1.0).fillna(0.0)
    weight_raw = pd.Series(0.0, index=idx)
    weight_raw[holding_raw == "btc"] = btc_w[holding_raw == "btc"]
    weight_raw[holding_raw == "gold"] = gold_w[holding_raw == "gold"]

    holding_state = holding_raw.where(is_rebalance_day).ffill().fillna("cash")
    weight_state = weight_raw.where(is_rebalance_day).ffill().fillna(0.0)

    holding_applied = holding_state.shift(1).fillna("cash")
    weight_applied = weight_state.shift(1).fillna(0.0)

    strat_ret = pd.Series(0.0, index=idx)
    is_btc = holding_applied == "btc"
    is_gold = holding_applied == "gold"
    strat_ret[is_btc] = btc_daily_ret[is_btc] * weight_applied[is_btc]
    strat_ret[is_gold] = gold_daily_ret[is_gold] * weight_applied[is_gold]

    position = (holding_applied != "cash").astype(int)
    return pd.DataFrame({"position": position, "returns": strat_ret}, index=idx)


def _simulate(
    price_df: pd.DataFrame,
    partner_symbol: str = "BTC/USDT",
    lookback_weeks_1: int = 4,
    lookback_weeks_2: int = 8,
    lookback_weeks_3: int = 12,
    vol_cap: float = 0.20,
    vol_window_days: int = 60,
    rebalance_weekday: int = 2,  # 0=Mon, 2=Wed (source's own choice)
) -> pd.DataFrame:
    df = _prep(price_df)
    gold_close = df["close"]
    start, end = df.index.min(), df.index.max()

    btc_close = _load_partner_close(partner_symbol, start, end)
    btc_close = btc_close.reindex(gold_close.index, method="ffill")

    lookbacks = [lookback_weeks_1, lookback_weeks_2, lookback_weeks_3]
    subs = [
        _single_lookback_sim(gold_close, btc_close, lb, vol_cap, vol_window_days, rebalance_weekday)
        for lb in lookbacks
    ]

    composite_ret = sum(s["returns"] for s in subs) / len(subs)
    composite_position = (sum(s["position"] for s in subs) > 0).astype(int)

    return pd.DataFrame({"position": composite_position, "returns": composite_ret}, index=gold_close.index)


def generate_signals(
    price_df: pd.DataFrame,
    partner_symbol: str = "BTC/USDT",
    lookback_weeks_1: int = 4,
    lookback_weeks_2: int = 8,
    lookback_weeks_3: int = 12,
    vol_cap: float = 0.20,
    vol_window_days: int = 60,
    rebalance_weekday: int = 2,
) -> pd.Series:
    result = _simulate(
        price_df, partner_symbol, lookback_weeks_1, lookback_weeks_2, lookback_weeks_3,
        vol_cap, vol_window_days, rebalance_weekday,
    )
    return result["position"]


def generate_returns(
    price_df: pd.DataFrame,
    partner_symbol: str = "BTC/USDT",
    lookback_weeks_1: int = 4,
    lookback_weeks_2: int = 8,
    lookback_weeks_3: int = 12,
    vol_cap: float = 0.20,
    vol_window_days: int = 60,
    rebalance_weekday: int = 2,
) -> pd.Series:
    result = _simulate(
        price_df, partner_symbol, lookback_weeks_1, lookback_weeks_2, lookback_weeks_3,
        vol_cap, vol_window_days, rebalance_weekday,
    )
    return result["returns"]
