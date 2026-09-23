"""Strategy: Donchian-breakout tactical rotation between an equity instrument
(the strategy's own price_df, e.g. QQQ/SPY) and Bitcoin, with a cash
fallback during consolidation ("Variant B": crypto-first priority).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-058):
Direct follow-up to accepted 2026-09-23-057 (Variant A, equity-first
priority QQQ/SPY-BTC Donchian rotation, Sharpe 1.65 QQQ / 1.22 SPY, grid
pass_fraction 0.722). Same source (Vojtko & Dujava, "Silicon vs. Satoshi:
Tactical Asset Rotation Between NASDAQ-100 and Bitcoin", SSRN 7055018,
https://quantpedia.com/silicon-vs-satoshi-tactical-asset-rotation-between-nasdaq-100-and-bitcoin/),
but this iteration tests the paper's own explicitly-disclosed "Variant B":
BTC checked FIRST for a breakout (hold BTC if breaking out), else check
equity (hold equity if breaking out), else cash. The paper's own reported
finding: Variant B produces higher absolute returns at short lookbacks
(5-day: 47.06% CAGR, the highest across all its configurations) but with
elevated volatility (33.11% vs Variant A's 25.85%), and degrades faster at
longer lookbacks (50-day Sharpe 0.846, BELOW all benchmarks) -- "indicating
that the Bitcoin-first ordering is less robust over longer horizons." This
iteration mechanically swaps only the priority ordering (same breakout
signal construction, same cash-fallback logic) to test that specific
paper-disclosed distinction directly against this repo's own data.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position,
        1 = in ANY breakout state (crypto or equity), 0 = cash)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns of the ACTUAL rotation portfolio: BTC return while in the
        crypto leg, equity return while in the equity leg, 0 while cash)
"""

from __future__ import annotations

import os
import sys
from datetime import timedelta

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_btc_aligned(equity_index: pd.DatetimeIndex, crypto_symbol: str = "BTC/USDT") -> pd.Series:
    from loaders import load_crypto

    start = equity_index.min() - timedelta(days=5)
    end = equity_index.max() + timedelta(days=2)
    btc_df = load_crypto(crypto_symbol, start, end, interval="1d")
    btc_df = _prep(btc_df)
    btc_close = btc_df["close"]

    if isinstance(equity_index, pd.DatetimeIndex) and equity_index.tz is not None:
        if btc_close.index.tz is None:
            btc_close = btc_close.tz_localize(equity_index.tz)
        else:
            btc_close = btc_close.tz_convert(equity_index.tz)
    else:
        if isinstance(btc_close.index, pd.DatetimeIndex) and btc_close.index.tz is not None:
            btc_close = btc_close.tz_localize(None)

    eq_idx = equity_index
    aligned = btc_close.reindex(btc_close.index.union(eq_idx)).sort_index().ffill()
    aligned = aligned.reindex(eq_idx)
    return aligned


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 20,
    crypto_symbol: str = "BTC/USDT",
) -> pd.Series:
    """Return a {0,1} "in-market" (either leg) position series."""
    df = _prep(price_df)
    equity_close = df["close"]
    btc_close = _load_btc_aligned(equity_close.index, crypto_symbol)

    equity_upper = equity_close.shift(1).rolling(lookback).max()
    btc_upper = btc_close.shift(1).rolling(lookback).max()

    equity_breakout = equity_close > equity_upper
    btc_breakout = btc_close > btc_upper

    in_market = (equity_breakout | btc_breakout).fillna(False)
    return in_market.astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    lookback: int = 20,
    crypto_symbol: str = "BTC/USDT",
) -> pd.Series:
    """Position-weighted daily returns of the actual rotation portfolio
    (Variant B: crypto-first priority -- BTC leg checked before equity)."""
    df = _prep(price_df)
    equity_close = df["close"]
    btc_close = _load_btc_aligned(equity_close.index, crypto_symbol)

    equity_upper = equity_close.shift(1).rolling(lookback).max()
    btc_upper = btc_close.shift(1).rolling(lookback).max()

    equity_breakout = equity_close > equity_upper
    btc_breakout = btc_close > btc_upper

    equity_ret = equity_close.pct_change().fillna(0.0)
    btc_ret = btc_close.pct_change().fillna(0.0)

    # Variant B priority: crypto first, then equity, else cash (0%).
    state_btc = btc_breakout.shift(1).fillna(False)
    state_equity = (~btc_breakout.shift(1).fillna(False)) & equity_breakout.shift(1).fillna(False)

    strategy_ret = pd.Series(0.0, index=equity_close.index)
    strategy_ret[state_btc] = btc_ret[state_btc]
    strategy_ret[state_equity] = equity_ret[state_equity]
    return strategy_ret
