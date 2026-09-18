"""Strategy: Monthly ETF rotation gate (200d SMA trend filter + ROC ranking).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per FabTrader's "ETF Rotation Strategy: A Four-Year Historical Backtest"
(https://fabtrader.in/blog/a-simple-peaceful-etf-rotation-strategy-that-delivered-32-cagr),
the source's own disclosed monthly rotation rule is: (1) TREND FILTER -- an
ETF must trade above its 200-day moving average to be eligible; (2)
MOMENTUM RANK -- eligible ETFs are ranked by trailing Rate-of-Change (ROC)
over a chosen lookback (source tests 1/2/3-month variants); (3) SELECT
top-N ranked ETFs, equal-weighted; (4) rebalance monthly (enter at month
open, exit at month close, re-rank).

Adapted to this repo's single-asset generate_signals/generate_returns
interface the same way the existing 5-asset momentum rotation gate
(2026-09-11-037/2026-09-11-110ish pattern) handles cross-asset signals:
the strategy internally loads a basket of US-tradable liquid proxy ETFs
(distinct universe from the source's Indian-market ETF list, since this
repo's data/loaders.py only fetches US-listed tickers via yfinance) via
data/loaders.py, computes the 200-day SMA trend filter + ROC rank for each
basket member at each month-end, and returns position=1 for the PRIMARY
(passed-in) asset only during months when it (a) passes its own 200d SMA
trend filter AND (b) is among the top_n ranked assets in the basket by
trailing ROC; flat otherwise.

Basket: QQQ, SPY, IWM, GLD, TLT, EFA, EEM (broad US, small-cap, gold,
long-treasuries, developed-ex-US, emerging-markets -- diversified
asset-class proxies analogous in spirit to the source's Nifty/BankNifty/
gold/silver/sector-ETF universe, adapted to US-listed instruments).

Signal logic
------------
- At each month-end (last trading day of the month present in the data),
  for every basket ETF: eligible = close > SMA(200); roc = close.pct_change
  over roc_lookback_months*21 trading days (approx).
- Rank eligible ETFs by roc descending; select top_n.
- Primary asset held (1) for the following month IF it was eligible AND
  in the top_n selected set at the most recent month-end; flat (0)
  otherwise.
- Position held constant through the month (no intra-month changes),
  re-evaluated only at month boundaries -- matches the source's "monthly
  reset" cadence.

Sources read this iteration:
- https://fabtrader.in/blog/a-simple-peaceful-etf-rotation-strategy-that-delivered-32-cagr
  (200d SMA trend filter, ROC ranking, top-N equal-weight, monthly
  open-to-close cycle, fully disclosed mechanical rule).

First strategy in this repo combining an explicit 200d-SMA ELIGIBILITY
gate with ROC-based cross-sectional RANKING in a single-asset basket-gate
adaptation (distinct from 2026-09-11-037's momentum-rank-only 5-asset gate
with no separate trend-filter eligibility step, and from GEM/dual-momentum
absolute-momentum gates which don't use a moving-average trend filter).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import sys
import os
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

BASKET = ["QQQ", "SPY", "IWM", "GLD", "TLT", "EFA", "EEM"]

_basket_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_basket_closes(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Load daily close for every basket ETF, reindexed/forward-filled to
    the primary asset's index. Cached across calls within a process."""
    from loaders import load_equity

    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    cache_key = (start, end)
    if cache_key in _basket_cache:
        return _basket_cache[cache_key]

    closes = {}
    for sym in BASKET:
        try:
            df = load_equity(sym, start, end)
            df = _prep(df)
            closes[sym] = df["close"]
        except Exception:
            continue

    basket_df = pd.DataFrame(closes)
    basket_df = basket_df.reindex(index).ffill()
    _basket_cache[cache_key] = basket_df
    return basket_df


def _month_end_mask(index: pd.DatetimeIndex) -> pd.Series:
    months = pd.Series(index.to_period("M"), index=index)
    is_last_of_month = months != months.shift(-1)
    is_last_of_month.iloc[-1] = True
    return is_last_of_month


def _rotation_position(
    primary_symbol_close: pd.Series,
    basket_df: pd.DataFrame,
    primary_col: str,
    trend_window: int,
    roc_lookback_months: int,
    top_n: int,
) -> pd.Series:
    index = primary_symbol_close.index
    roc_days = max(1, roc_lookback_months * 21)

    sma = basket_df.rolling(trend_window).mean()
    eligible = basket_df > sma
    roc = basket_df.pct_change(roc_days)

    month_end = _month_end_mask(index)
    month_end_positions = [i for i, flag in enumerate(month_end) if flag]

    position = pd.Series(0, index=index, dtype=int)
    current_selected = False

    for idx_pos in range(len(index)):
        # Update selection decision at each month-end for the FOLLOWING period.
        if idx_pos in month_end_positions:
            row_eligible = eligible.iloc[idx_pos]
            row_roc = roc.iloc[idx_pos]
            valid_syms = [s for s in basket_df.columns if bool(row_eligible.get(s, False)) and pd.notna(row_roc.get(s))]
            ranked = sorted(valid_syms, key=lambda s: row_roc[s], reverse=True)
            selected = set(ranked[:top_n])
            current_selected = primary_col in selected
        position.iloc[idx_pos] = 1 if current_selected else 0

    return position


def generate_signals(
    price_df: pd.DataFrame,
    primary_symbol: str = "QQQ",
    trend_window: int = 200,
    roc_lookback_months: int = 3,
    top_n: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series based on monthly ETF rotation."""
    df = _prep(price_df)
    close = df["close"]
    basket_df = _load_basket_closes(df.index)

    if primary_symbol not in basket_df.columns:
        basket_df = basket_df.copy()
        basket_df[primary_symbol] = close

    return _rotation_position(
        close, basket_df, primary_symbol, trend_window, roc_lookback_months, top_n
    )


def generate_returns(
    price_df: pd.DataFrame,
    primary_symbol: str = "QQQ",
    trend_window: int = 200,
    roc_lookback_months: int = 3,
    top_n: int = 3,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        primary_symbol=primary_symbol,
        trend_window=trend_window,
        roc_lookback_months=roc_lookback_months,
        top_n=top_n,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
