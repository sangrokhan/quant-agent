"""Strategy: SPY/QQQ pairs trading via regression hedge ratio + spread z-score.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-098):
SPY and QQQ are highly correlated large-cap US equity index ETFs (~0.85
60-day correlation per source). Per quantifiedstrategies.com's correlation-
trading article: estimate a rolling regression hedge ratio (beta) between
the two, construct the spread = QQQ - beta*SPY, z-score it against a
rolling mean/std, and trade mean-reversion when the z-score exceeds +/-
entry_z (source recommends 1.5-2 std), exiting when it reverts to 0. This
differs from the already-tested ETH/BTC pairs strategy (2026-09-04-083,
rejected) by (a) using equities not crypto, and (b) using a proper rolling
OLS regression-estimated hedge ratio rather than a raw price ratio.

This repo's generate_returns must return a SINGLE return series (validator
contract), so this strategy synthesizes a long-QQQ/short-SPY (or reverse)
spread-trade return series directly, using the strategy's own beta-weighted
position sizing (dollar-neutral: 1 unit QQQ vs beta units SPY, normalized).
Since SAFETY.md disallows real order-placement code but does not disallow
back-testing a market-neutral long/short spread synthetically in a backtest
context (no live shorting execution occurs here, only return-series
arithmetic), this is implemented as a pure numerical spread-return
calculation, consistent with how the already-tested and already-accepted-
for-testing 2026-09-04-083 pairs strategy was implemented.

Signal logic
------------
- Rolling `hedge_window`-day OLS hedge ratio (beta) of QQQ close on SPY
  close: beta[t] = Cov(QQQ, SPY) / Var(SPY) over the trailing window.
- Spread[t] = QQQ_close[t] - beta[t] * SPY_close[t].
- Z-score[t] = (Spread[t] - rolling_mean(Spread, z_window)) /
  rolling_std(Spread, z_window).
- Entry: |z| >= entry_z. If z <= -entry_z: long the spread (long QQQ, short
  beta*SPY dollar-weighted). If z >= entry_z: short the spread (short QQQ,
  long beta*SPY dollar-weighted).
- Exit: z crosses back through 0 (or |z| < exit_z, default 0.25), or after
  max_hold_days.
- Daily spread return while in a trade: r[t] = (QQQ_ret[t] - beta *
  SPY_ret[t]) * direction, where direction = +1 (long spread) or -1 (short
  spread), QQQ_ret/SPY_ret are simple daily returns.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position,
        1 whenever a spread trade is open)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns from the spread trade)

Note: `price_df` here is expected to be QQQ's OHLCV (the "primary" symbol
passed by the grid harness); SPY is fetched internally via data/loaders.py,
mirroring the pattern used in 2026-09-04_dual_momentum_rotation.py.
"""

from __future__ import annotations

import sys
import os

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _simulate(
    price_df: pd.DataFrame,
    hedge_symbol: str = "SPY",
    hedge_window: int = 60,
    z_window: int = 60,
    entry_z: float = 2.0,
    exit_z: float = 0.25,
    max_hold_days: int = 20,
) -> pd.DataFrame:
    df = _prep(price_df)
    primary_close = df["close"]
    start, end = df.index.min(), df.index.max()
    if getattr(start, "tzinfo", None) is not None:
        start = start.tz_localize(None)
    if getattr(end, "tzinfo", None) is not None:
        end = end.tz_localize(None)
    hedge_df = _prep(load_equity(hedge_symbol, start, end))
    hedge_close = hedge_df["close"].reindex(primary_close.index, method="ffill")

    primary_ret = primary_close.pct_change().fillna(0.0)
    hedge_ret = hedge_close.pct_change().fillna(0.0)

    cov = primary_close.rolling(hedge_window).cov(hedge_close)
    var = hedge_close.rolling(hedge_window).var()
    beta = (cov / var).replace([float("inf"), float("-inf")], None)

    spread = primary_close - beta * hedge_close
    spread_mean = spread.rolling(z_window).mean()
    spread_std = spread.rolling(z_window).std()
    zscore = (spread - spread_mean) / spread_std

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    returns = pd.Series(0.0, index=df.index)

    in_trade = False
    direction = 0
    entry_idx = 0
    entry_beta = 0.0

    for i in range(n):
        z = zscore.iloc[i]
        if not in_trade:
            if pd.notna(z) and pd.notna(beta.iloc[i]):
                if z <= -entry_z:
                    in_trade, direction, entry_idx, entry_beta = True, 1, i, beta.iloc[i]
                elif z >= entry_z:
                    in_trade, direction, entry_idx, entry_beta = True, -1, i, beta.iloc[i]
        else:
            held = i - entry_idx
            day_ret = direction * (primary_ret.iloc[i] - entry_beta * hedge_ret.iloc[i])
            returns.iloc[i] = day_ret
            position.iloc[i] = 1
            exit_now = (pd.notna(z) and abs(z) < exit_z) or held >= max_hold_days
            if exit_now:
                in_trade = False
                direction = 0

    return pd.DataFrame({"position": position, "returns": returns}, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    hedge_symbol: str = "SPY",
    hedge_window: int = 60,
    z_window: int = 60,
    entry_z: float = 2.0,
    exit_z: float = 0.25,
    max_hold_days: int = 20,
) -> pd.Series:
    result = _simulate(price_df, hedge_symbol, hedge_window, z_window, entry_z, exit_z, max_hold_days)
    return result["position"]


def generate_returns(
    price_df: pd.DataFrame,
    hedge_symbol: str = "SPY",
    hedge_window: int = 60,
    z_window: int = 60,
    entry_z: float = 2.0,
    exit_z: float = 0.25,
    max_hold_days: int = 20,
) -> pd.Series:
    result = _simulate(price_df, hedge_symbol, hedge_window, z_window, entry_z, exit_z, max_hold_days)
    return result["returns"]
