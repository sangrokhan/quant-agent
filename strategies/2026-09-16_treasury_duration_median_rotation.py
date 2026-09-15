"""Strategy: U.S. Treasury ETF "Median" duration-rotation strategy.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Malhotra, Puppala & Pinsky, "Duration Rotation in U.S. Treasury
Fixed-Income ETFs: Evidence for a 'Median' Strategy", FinTech 2026, 5(2), 29
(https://www.mdpi.com/2674-1032/5/2/29, visited this iteration via
browser_exec after web_search's DDGS backend TLS-errored/failed): across six
U.S. Treasury ETFs spanning the maturity spectrum (SHV, SHY, IEI, IEF, TLH,
TLT), ranking by prior-period total return and reinvesting in the MIDDLE two
(not the top-2 "Winners", contrary to conventional momentum logic) produces
better risk-adjusted returns than Buy & Hold, a Winners-momentum rotation, or
a Losers-contrarian rotation, at semi-annual rebalancing. Source found this
holds 2007-2025 (Sharpe 0.606 vs 0.494 benchmark, MDD -11.6% vs -14.4%,
Newey-West HAC p=0.031, Lo(2002) p=0.014, walk-forward p=0.0005).

Framework adaptation note: this is fundamentally a 6-asset cross-sectional
rotation strategy, not a single-symbol signal, so (like
strategies/2026-09-08_pairs_zscore_cointecointegration.py's pairs-trading
adaptation) it fetches the OTHER basket members internally via
data/loaders.py, keyed off price_df's own date range. ``own_symbol`` names
which of the 6 basket tickers price_df itself represents (must be passed
explicitly by the caller/grid config -- there is no way to recover a
ticker's identity from an OHLCV DataFrame alone). generate_signals returns
1 (long) for the periods when own_symbol lands in the middle
group of the ranking (or one of the other groups, if ``target`` != "median",
to let a single implementation reproduce the source's Winners/Losers control
rotations too), else 0.

Signal logic
------------
- At each rebalance_days-bar mark, rank the trailing lookback_days total
  return of all 6 basket tickers (SHV, SHY, IEI, IEF, TLH, TLT).
- Split the 6 into three pairs: top-2 (Winners), middle-2 (Median),
  bottom-2 (Losers) by that ranking.
- position = 1 for the following rebalance_days-bar holding period if
  own_symbol is in the ``target`` group (default "median"), else 0.
- No stop-loss/time-stop -- the source's edge is a periodic-rebalance
  cross-sectional selection effect, not a per-trade timing signal.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import os
import sys
from datetime import timedelta

import numpy as np
import pandas as pd

DEFAULT_BASKET = ["SHV", "SHY", "IEI", "IEF", "TLH", "TLT"]


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_basket_closes(index: pd.DatetimeIndex, basket: list) -> pd.DataFrame:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    start = index.min()
    end = index.max() + timedelta(days=2)
    closes = {}
    for ticker in basket:
        try:
            df = _prep(load_equity(ticker, start, end))
            closes[ticker] = df["close"]
        except Exception:
            continue
    out = pd.DataFrame(closes)
    out = out.reindex(index).ffill()
    return out


def _rotation_signal(
    price_df: pd.DataFrame,
    own_symbol: str,
    basket: list,
    lookback_days: int,
    rebalance_days: int,
    target: str,
) -> pd.Series:
    df = _prep(price_df)
    closes = _load_basket_closes(df.index, basket)
    if own_symbol not in closes.columns:
        # Own series wasn't fetchable independently (e.g. loader quirk) --
        # fall back to price_df's own close under its declared name.
        closes[own_symbol] = df["close"].reindex(closes.index).ffill()

    position = pd.Series(0, index=df.index, dtype=int)
    n = len(df.index)
    rebalance_idxs = list(range(lookback_days, n, rebalance_days))
    for start_i in rebalance_idxs:
        window = closes.iloc[start_i - lookback_days : start_i]
        if window.isna().any().any() or len(window) < lookback_days:
            continue
        period_returns = (window.iloc[-1] / window.iloc[0]) - 1.0
        period_returns = period_returns.dropna()
        if own_symbol not in period_returns.index or len(period_returns) < 4:
            continue
        ranked = period_returns.sort_values(ascending=False)
        half = len(ranked) // 2
        # even split into thirds when basket size is a multiple of 3, else
        # generic top/middle/bottom by ranking position for degenerate baskets
        third = max(1, len(ranked) // 3)
        winners = set(ranked.index[:third])
        losers = set(ranked.index[-third:])
        median_group = set(ranked.index) - winners - losers

        if target == "winners":
            selected = winners
        elif target == "losers":
            selected = losers
        else:
            selected = median_group

        end_i = min(start_i + rebalance_days, n)
        if own_symbol in selected:
            position.iloc[start_i:end_i] = 1

    return position


def generate_signals(
    price_df: pd.DataFrame,
    own_symbol: str = "IEF",
    basket: list = None,
    lookback_days: int = 126,
    rebalance_days: int = 126,
    target: str = "median",
) -> pd.Series:
    basket = basket if basket is not None else list(DEFAULT_BASKET)
    df = _prep(price_df)
    position = _rotation_signal(df, own_symbol, basket, lookback_days, rebalance_days, target)
    return position.reindex(df.index).fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    own_symbol: str = "IEF",
    basket: list = None,
    lookback_days: int = 126,
    rebalance_days: int = 126,
    target: str = "median",
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        df,
        own_symbol=own_symbol,
        basket=basket,
        lookback_days=lookback_days,
        rebalance_days=rebalance_days,
        target=target,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    # position at t determines exposure to the t -> t+1 return (avoid
    # look-ahead: shift position by 1 bar)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
