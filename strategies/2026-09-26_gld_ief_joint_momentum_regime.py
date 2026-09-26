"""Strategy: Joint Gold-Momentum + Treasury-Momentum Regime Filter (GLD).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-023):
Per QuantPedia's "Cross-Asset Price-Based Regimes for Gold"
(https://quantpedia.com/cross-asset-price-based-regimes-for-gold/,
browser_exec, own-research 4 Jan 2026): gold's forward returns are
conditioned by the JOINT momentum state of (i) gold itself and (ii)
long-duration U.S. Treasuries (IEF). The source's own "most potent version"
(12-Month Gold-Treasury Regime Filter): at each monthly rebalancing date,
compute the trailing N-month total return of GLD and the trailing N-month
total return of IEF; hold 100% GLD if and only if BOTH are strictly
positive (State 1: "Gold up AND Treasuries up" -- falling real yields,
easing conditions); otherwise flat (0% allocation / cash). The source
reports this joint-momentum state 1 filter empirically dominates every
single-signal (gold-only-momentum or IEF-only-momentum) variant and every
other joint state on Sharpe, Calmar, and cumulative return.

First joint gold-momentum + treasury-momentum 2-factor regime gate for GLD
in this repo -- distinct from every prior GLD/TLT/IEF RATIO-based gate
(which use the RATIO of two asset prices/MAs), since this uses each asset's
OWN independent momentum sign, combined via AND.

Interface contract:
    generate_signals(price_df, **params) -> pd.Series ({0,1})
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

_ief_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_ief() -> pd.Series:
    key = "IEF"
    if key not in _ief_cache:
        import sys
        import os

        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
        from loaders import load_equity  # noqa: E402

        df = load_equity("IEF", datetime(2003, 1, 1), datetime(2026, 12, 31), interval="1d")
        df = _prep(df)
        _ief_cache[key] = df["close"]
    return _ief_cache[key]


def generate_signals(
    price_df: pd.DataFrame,
    momentum_window_days: int = 252,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    momentum_window_days approximates the source's monthly N-month lookback
    in trading days (e.g. 252 trading days ~= 12 months).
    """
    df = _prep(price_df)
    close = df["close"]

    gold_momentum = close.pct_change(momentum_window_days)

    ief_close = _get_ief().reindex(close.index, method="ffill")
    ief_momentum = ief_close.pct_change(momentum_window_days)

    both_positive = ((gold_momentum > 0) & (ief_momentum > 0)).fillna(False)
    position = both_positive.astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
