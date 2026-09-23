"""Strategy: Donchian-breakout tactical rotation between an equity instrument
(the strategy's own price_df, e.g. QQQ/SPY) and Bitcoin, with a cash
fallback during consolidation ("Variant A": equity-first priority).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-057):
Per Radovan Vojtko & Cyril Dujava's Quantpedia/SSRN paper "Silicon vs.
Satoshi: Tactical Asset Rotation Between NASDAQ-100 and Bitcoin"
(https://quantpedia.com/silicon-vs-satoshi-tactical-asset-rotation-between-nasdaq-100-and-bitcoin/,
SSRN abstract=7055018, read via browser_exec this iteration -- web_search's
DDGS backend surfaced only Korean-localized low-quality SERP snippets for
the discovery queries), Bitcoin and NASDAQ-100 tech stocks compete for the
same finite pool of retail attention/speculative capital (Barber & Odean
2000 overconfidence framework; Liu & Tsyvinski 2021 crypto time-series
momentum + attention-proxy forecasting). The paper's own disclosed signal
construction: for lookback window w, upper channel Ut(w) = max(close over
the trailing w bars, excluding today); a breakout signal fires when today's
close exceeds that bound. Three-state rotation: if the equity leg (QQQ) is
breaking out, hold it; else if the crypto leg (BTC) is breaking out, hold
it; else 100% cash (0% return) -- this is the paper's "Variant A" (equity
first priority), reported as the more risk-adjusted-favorable ordering
(higher Sharpe/Calmar, lower drawdown vs Variant B's crypto-first
ordering) across the paper's own 2019-2025 backtest (Sharpe up to 1.69,
Calmar >2.2, 51-79% drawdown compression vs buy-and-hold benchmarks).
Genuinely novel in this repo: first CROSS-ASSET rotation strategy (equity
vs crypto vs cash three-state allocation) rather than a single-instrument
entry/exit rule or a same-asset-class dual-momentum vote.

Data note: this repo's generate_returns_fn contract is per-symbol
(single price_df in, single return series out), so `price_df` is treated
as the equity leg (paper's QQQ); the crypto leg is always BTC/USDT,
fetched internally via data/loaders.py's load_crypto and aligned onto
price_df's own trading-day index (forward-filled, matching the paper's own
data-alignment methodology of resampling continuous BTC onto the equity
trading calendar). When this strategy is grid-tested against a "crypto"
symbol slot (e.g. ETH/USDT as price_df), price_df is instead treated as the
crypto leg and BTC/USDT is still the fixed comparison asset (skipped -- see
grid script) since the paper's own construction is equity-vs-BTC
specifically, not generic dual-crypto rotation.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position,
        1 = in ANY breakout state (equity or crypto), 0 = cash)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns of the ACTUAL rotation portfolio: equity return while in
        the equity leg, BTC return while in the crypto leg, 0 while cash)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

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
    # Align BTC's continuous calendar onto the equity trading-day index
    # (forward-fill, matching the paper's own alignment methodology).
    # Normalize tz on BOTH sides to the equity index's own tz-awareness so
    # the returned series' index exactly matches equity_index (grid_test.py
    # reindexes vol-regime masks against this index and needs tz parity).
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
    (Variant A: equity-first priority -- equity leg checked before crypto)."""
    df = _prep(price_df)
    equity_close = df["close"]
    btc_close = _load_btc_aligned(equity_close.index, crypto_symbol)

    equity_upper = equity_close.shift(1).rolling(lookback).max()
    btc_upper = btc_close.shift(1).rolling(lookback).max()

    equity_breakout = equity_close > equity_upper
    btc_breakout = btc_close > btc_upper

    equity_ret = equity_close.pct_change().fillna(0.0)
    btc_ret = btc_close.pct_change().fillna(0.0)

    # Variant A priority: equity first, then crypto, else cash (0%).
    # Signal computed on day t's close is applied to day t+1's return
    # (shift by 1 to avoid look-ahead -- act on yesterday's signal).
    state_equity = equity_breakout.shift(1).fillna(False)
    state_btc = (~equity_breakout.shift(1).fillna(False)) & btc_breakout.shift(1).fillna(False)

    strategy_ret = pd.Series(0.0, index=equity_close.index)
    strategy_ret[state_equity] = equity_ret[state_equity]
    strategy_ret[state_btc] = btc_ret[state_btc]
    return strategy_ret
