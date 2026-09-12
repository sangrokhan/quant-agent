"""Strategy: BTC/ETH/SOL 3-way relative-strength rotation with an
absolute-momentum cash gate (goes flat -- 0% invested -- when even the
current relative-strength leader's own momentum is negative, rather than
always being fully invested in whichever asset is least-bad).

Direct follow-up to 2026-09-13-035 (plain always-invested 3-way rotation,
decisively rejected: best Sharpe 0.339, MDD 79-95% across a 15-combo
sweep). That entry's own notes flagged the catastrophic MDD as caused by
the "always fully invested, no cash/diversification" design -- this
strategy adds Gary Antonacci's Dual-Momentum-style absolute-momentum gate
(already validated as a real MDD-reduction mechanism in this repo's
2026-09-04-097 GEM-style pairwise BTC/ETH dual momentum, and accepted in
several single-asset absolute-momentum variants) on top of the *relative*
3-way leader-selection from -035: hold the current leader only if the
leader's OWN trailing momentum is positive; otherwise go to cash (flat,
zero return, zero drawdown exposure) until some asset's momentum turns
positive again.

Signal logic
------------
- Same 3-way relative-strength leader selection as 2026-09-13-035
  (highest trailing `momentum_window`-day return among BTC/ETH/SOL).
- Absolute-momentum gate: only actually hold the leader if the leader's
  own momentum score > 0; otherwise position = cash (0% invested, 0%
  return that day).
- Decision made using yesterday's close (info as of t-1 applied to
  today's return, this repo's standard shift convention).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0=cash, 1=BTC,
        2=ETH, 3=SOL)
    generate_returns(price_df, **params) -> pd.Series (daily strategy
        returns; 0.0 whenever in cash)

Note: `price_df` here is expected to be BTC/USDT's OHLCV (the "primary"
symbol passed by the grid harness); ETH/USDT and SOL/USDT are fetched
internally via data/loaders.py.
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
    momentum_window: int = 21,
    min_hold_days: int = 3,
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

    valid = mom_df.notna().all(axis=1)
    leader = mom_df.fillna(-np.inf).idxmax(axis=1)
    leader_mom = mom_df.fillna(-np.inf).max(axis=1)
    # Absolute momentum gate: cash if leader's own momentum <= 0.
    holding = leader.where(valid & (leader_mom > 0), "CASH")

    holding_filled = holding.ffill().fillna("CASH")
    if min_hold_days > 1:
        current = None
        days_held = 0
        result = []
        for val in holding_filled:
            if val != current and (current is None or days_held >= min_hold_days):
                current = val
                days_held = 1
            else:
                days_held += 1
            result.append(current)
        held = pd.Series(result, index=holding_filled.index)
    else:
        held = holding_filled

    rets = {name: c.pct_change().fillna(0.0) for name, c in closes.items()}
    ret_df = pd.DataFrame(rets)

    held_shifted = held.shift(1).fillna("CASH")
    strat_ret = pd.Series(0.0, index=btc_close.index)
    for name in ["BTC", "ETH", "SOL"]:
        mask = (held_shifted == name)
        strat_ret[mask] = ret_df.loc[mask, name]
    # CASH -> strat_ret stays 0.0

    position_map = {"CASH": 0, "BTC": 1, "ETH": 2, "SOL": 3}
    position = held.map(position_map).fillna(0).astype(int)

    return pd.DataFrame({"position": position, "returns": strat_ret}, index=btc_close.index)


def generate_signals(
    price_df: pd.DataFrame,
    momentum_window: int = 21,
    min_hold_days: int = 3,
) -> pd.Series:
    return _simulate(price_df, momentum_window=momentum_window, min_hold_days=min_hold_days)["position"]


def generate_returns(
    price_df: pd.DataFrame,
    momentum_window: int = 21,
    min_hold_days: int = 3,
) -> pd.Series:
    return _simulate(price_df, momentum_window=momentum_window, min_hold_days=min_hold_days)["returns"]
