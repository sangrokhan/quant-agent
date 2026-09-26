"""Strategy: QQQ-BTC Donchian Breakout Rotation with Cash Fallback.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-024):
Per QuantPedia's "Silicon vs. Satoshi: Tactical Asset Rotation Between
NASDAQ-100 and Bitcoin" (https://quantpedia.com/silicon-vs-satoshi-tactical-asset-rotation-between-nasdaq-100-and-bitcoin/,
browser_exec, own-research, Cyril Dujava, 2 July 2026, fully disclosed): a
three-state rotation among QQQ, BTC, and cash using a Donchian-style price
channel breakout. For lookback window w, the upper channel bound at time t
is U_t(w) = max(close[t-w:t-1]); a breakout fires when today's close
exceeds U_t(w). Variant A (source's own risk-adjusted-best): check QQQ for
breakout first (if QQQ breaks out, hold QQQ); else check BTC (if BTC breaks
out, hold BTC); else hold cash (0% return). Source's own 2019-2025 QQQ+BTC
backtest: Sharpe 1.15-1.69 across w in {5,10,...,50} days (20-day: Sharpe
1.68, Calmar 2.25, MDD -17.6%), all comfortably beating a 50/50 QQQ/BTC
buy-and-hold benchmark (Sharpe 1.19, MDD -59%) and 100% BTC buy-and-hold
(MDD -76.6%) via the cash-fallback drawdown compression mechanism.

First QQQ-BTC Donchian-breakout 3-state rotation-with-cash-fallback
strategy in this repo. Adapted to the single-asset generate_returns(price_df,
**params) contract: price_df is treated as QQQ (the primary/first-priority
asset per source's Variant A); BTC/USDT is fetched internally via
data/loaders.py.

Interface contract:
    generate_signals(price_df, **params) -> pd.Series ({0,1,2}: 0=cash, 1=QQQ, 2=BTC)
    generate_returns(price_df, **params) -> pd.Series (daily blended returns)
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

_btc_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_btc() -> pd.Series:
    key = "BTC"
    if key not in _btc_cache:
        import sys
        import os

        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
        from loaders import load_crypto  # noqa: E402

        df = load_crypto("BTC/USDT", datetime(2017, 1, 1), datetime(2026, 12, 31), interval="1d")
        df = _prep(df)
        _btc_cache[key] = df["close"]
    return _btc_cache[key]


def generate_signals(
    price_df: pd.DataFrame,
    lookback_window: int = 20,
) -> pd.Series:
    """Return a series of {0,1,2}: 0=cash, 1=QQQ(primary), 2=BTC."""
    df = _prep(price_df)
    qqq_close = df["close"]

    btc_close = _get_btc().reindex(qqq_close.index, method="ffill")

    qqq_upper = qqq_close.shift(1).rolling(lookback_window).max()
    btc_upper = btc_close.shift(1).rolling(lookback_window).max()

    qqq_breakout = (qqq_close > qqq_upper).fillna(False)
    btc_breakout = (btc_close > btc_upper).fillna(False)

    # Variant A priority: QQQ first, then BTC, else cash.
    state = pd.Series(0, index=df.index, dtype=int)
    state[btc_breakout] = 2
    state[qqq_breakout] = 1  # QQQ takes priority, overwrites BTC where both true
    return state


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Blended daily returns depending on which asset (or cash) is held."""
    df = _prep(price_df)
    qqq_close = df["close"]
    qqq_ret = qqq_close.pct_change().fillna(0.0)

    btc_close = _get_btc().reindex(qqq_close.index, method="ffill")
    btc_ret = btc_close.pct_change().fillna(0.0)

    state = generate_signals(price_df, **kwargs)
    state_lagged = state.shift(1).fillna(0).astype(int)

    strategy_ret = pd.Series(0.0, index=df.index)
    strategy_ret[state_lagged == 1] = qqq_ret[state_lagged == 1]
    strategy_ret[state_lagged == 2] = btc_ret[state_lagged == 2]
    # state_lagged == 0 -> cash, 0% return (already initialized)
    return strategy_ret
