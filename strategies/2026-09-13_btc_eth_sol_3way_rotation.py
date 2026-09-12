"""Strategy: BTC/ETH/SOL 3-way relative-strength rotation (always-invested,
holds whichever of the three assets has the strongest trailing momentum).

Source: Lukra.ai's "Crypto Rotation Strategies: How AI Allocates Across
BTC, ETH, and SOL" (https://lukra.ai/blog/crypto-rotation-strategy-btc-eth-sol,
read this iteration via browser_exec -- web_search DDGS backend returned
no results / TLS errors on the queries attempted this iteration, Bing SERP
fallback used throughout): "The model measures 7-day, 14-day, and 30-day
relative momentum for each asset. When one asset is dramatically
outperforming peers with strengthening momentum, it receives higher
allocation... This isn't pure trend-following -- it's relative momentum."
No exact numeric formula or on-chain/sentiment data is available to this
repo (single-symbol OHLCV loaders only), so this strategy time-series-
adapts the disclosed CORE mechanism -- ranking trailing momentum across
the three assets and rotating into the current leader -- using only
price data.

This is a genuine first in this repo: every prior crypto rotation
strategy (2026-09-04-083/108, 2026-09-08-084) is a PAIRWISE BTC/ETH
rotation or mean-reversion spread; none include SOL/USDT or extend to a
3-way relative-strength ranking. SOL/USDT itself only entered this repo's
knowledge base in the current cron trigger's earlier iterations
(2026-09-13-027 through -031/-033), always as a standalone single-asset
test, never as a rotation candidate alongside BTC/ETH.

Signal logic
------------
- For each of BTC/USDT, ETH/USDT, SOL/USDT compute trailing
  `momentum_window`-day total return (close[t]/close[t-momentum_window]-1).
- Each day, hold the single asset with the HIGHEST trailing momentum
  score (always fully invested in exactly one of the three -- never
  flat), decided using yesterday's close (info as of t-1 applied to
  today's return, this repo's standard shift convention).
- No minimum-hold/rebalance-threshold smoothing in the base version (adds
  unnecessary complexity for a first test of the core ranking mechanism);
  a `min_hold_days` parameter is exposed to reduce whipsaw/turnover if
  the base version churns too much.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (categorical-as-int:
        0=BTC, 1=ETH, 2=SOL -- NOT a flat/long distinction, since this
        strategy is always invested in one of the three assets)
    generate_returns(price_df, **params) -> pd.Series (daily strategy
        returns from whichever asset is currently held)

Note: `price_df` here is expected to be BTC/USDT's OHLCV (the "primary"
symbol passed by the grid harness); ETH/USDT and SOL/USDT are fetched
internally via data/loaders.py, mirroring the pattern used in
2026-09-04_eth_btc_relative_strength_rotation.py.
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


def _simulate(
    price_df: pd.DataFrame,
    momentum_window: int = 14,
    min_hold_days: int = 1,
) -> pd.DataFrame:
    """`price_df` is treated as BTC/USDT's OHLCV; ETH/USDT and SOL/USDT are
    fetched internally as the other two rotation candidates."""
    btc_df = _prep(price_df)
    btc_close = btc_df["close"]
    start, end = btc_df.index.min(), btc_df.index.max()
    if getattr(start, "tzinfo", None) is not None:
        start = start.tz_localize(None)
    if getattr(end, "tzinfo", None) is not None:
        end = end.tz_localize(None)

    eth_close = _prep(load_crypto("ETH/USDT", start, end))["close"].reindex(btc_close.index, method="ffill")
    sol_close = _prep(load_crypto("SOL/USDT", start, end))["close"].reindex(btc_close.index, method="ffill")

    closes = {"BTC": btc_close, "ETH": eth_close, "SOL": sol_close}
    momentum = {name: c.pct_change(momentum_window) for name, c in closes.items()}
    mom_df = pd.DataFrame(momentum)

    # Leader = asset with highest trailing momentum score each day.
    # NaN-safe: require all 3 momentum scores present before ranking.
    valid = mom_df.notna().all(axis=1)
    leader = mom_df.fillna(-np.inf).idxmax(axis=1)
    leader = leader.where(valid)

    # Apply min_hold_days: only switch leader if it's held for at least
    # min_hold_days days (reduces whipsaw/turnover).
    leader_filled = leader.ffill()
    if min_hold_days > 1:
        held = leader_filled.copy()
        current = None
        days_held = 0
        result = []
        for val in leader_filled:
            if val != current and (current is None or days_held >= min_hold_days):
                current = val
                days_held = 1
            else:
                days_held += 1
            result.append(current)
        held = pd.Series(result, index=leader_filled.index)
    else:
        held = leader_filled

    rets = {name: c.pct_change().fillna(0.0) for name, c in closes.items()}
    ret_df = pd.DataFrame(rets)

    held_shifted = held.shift(1)
    strat_ret = pd.Series(0.0, index=btc_close.index)
    for name in ["BTC", "ETH", "SOL"]:
        mask = (held_shifted == name).fillna(False)
        strat_ret[mask] = ret_df.loc[mask, name]

    position_map = {"BTC": 0, "ETH": 1, "SOL": 2}
    position = held.map(position_map).fillna(0).astype(int)

    return pd.DataFrame({"position": position, "returns": strat_ret}, index=btc_close.index)


def generate_signals(
    price_df: pd.DataFrame,
    momentum_window: int = 14,
    min_hold_days: int = 1,
) -> pd.Series:
    return _simulate(price_df, momentum_window=momentum_window, min_hold_days=min_hold_days)["position"]


def generate_returns(
    price_df: pd.DataFrame,
    momentum_window: int = 14,
    min_hold_days: int = 1,
) -> pd.Series:
    return _simulate(price_df, momentum_window=momentum_window, min_hold_days=min_hold_days)["returns"]
