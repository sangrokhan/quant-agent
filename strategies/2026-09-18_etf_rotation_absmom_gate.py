"""Strategy: Monthly ETF rotation gate + absolute-momentum overlay (200d SMA
trend filter + ROC ranking + require primary's own ROC > 0), rescue attempt.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Direct fix attempt for the prior near-miss 2026-09-18-069 (Monthly ETF
Rotation, 200d SMA + ROC ranking + top-N, QQQ Sharpe 0.939/MDD 0.286 both
narrowly missed the threshold, everything else passed). This iteration
adds one extra absolute-momentum condition on top of the identical
relative-ranking logic: the primary asset must not only be top-N ranked
AND above its 200d SMA, but its own trailing ROC over the ranking lookback
must ALSO be strictly positive (require_positive_roc=True). This targets
the specific failure mode noted in -069's own log: "always holding top-N
regardless of absolute momentum sign" -- i.e. being top-ranked in a falling
basket (where even the "best" ETF has negative momentum) can still trigger
a hold under -069's pure relative-rank rule, contributing to the MDD/Sharpe
miss. Adding an absolute-momentum floor should flatten the primary asset
during broad basket-wide drawdowns that the 200d-SMA eligibility filter
alone didn't fully catch (SMA(200) lags; a fresh downturn can persist above
a still-elevated 200d average for months).

Basket, ranking mechanics, and all other parameters are otherwise IDENTICAL
to 2026-09-18-069 -- this isolates whether the absolute-momentum floor
alone rescues the near-miss.

Sources read this iteration: same as 2026-09-18-069
(https://fabtrader.in/blog/a-simple-peaceful-etf-rotation-strategy-that-delivered-32-cagr)
-- this rescue attempt's absolute-momentum-floor addition is this repo's
own extension, not separately sourced (a common, standard "dual momentum"
absolute+relative combination per academic dual-momentum literature
already referenced elsewhere in this repo's GEM-family strategies).

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
    require_positive_roc: bool = True,
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
        if idx_pos in month_end_positions:
            row_eligible = eligible.iloc[idx_pos]
            row_roc = roc.iloc[idx_pos]
            valid_syms = [s for s in basket_df.columns if bool(row_eligible.get(s, False)) and pd.notna(row_roc.get(s))]
            ranked = sorted(valid_syms, key=lambda s: row_roc[s], reverse=True)
            selected = set(ranked[:top_n])
            primary_selected = primary_col in selected
            if require_positive_roc and primary_selected:
                primary_roc_val = row_roc.get(primary_col)
                primary_selected = bool(pd.notna(primary_roc_val) and primary_roc_val > 0)
            current_selected = primary_selected
        position.iloc[idx_pos] = 1 if current_selected else 0

    return position


def generate_signals(
    price_df: pd.DataFrame,
    primary_symbol: str = "QQQ",
    trend_window: int = 200,
    roc_lookback_months: int = 3,
    top_n: int = 3,
    require_positive_roc: bool = True,
) -> pd.Series:
    """Return a {0,1} long/flat position series based on monthly ETF rotation."""
    df = _prep(price_df)
    close = df["close"]
    basket_df = _load_basket_closes(df.index)

    if primary_symbol not in basket_df.columns:
        basket_df = basket_df.copy()
        basket_df[primary_symbol] = close

    return _rotation_position(
        close, basket_df, primary_symbol, trend_window, roc_lookback_months, top_n,
        require_positive_roc=require_positive_roc,
    )


def generate_returns(
    price_df: pd.DataFrame,
    primary_symbol: str = "QQQ",
    trend_window: int = 200,
    roc_lookback_months: int = 3,
    top_n: int = 3,
    require_positive_roc: bool = True,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        primary_symbol=primary_symbol,
        trend_window=trend_window,
        roc_lookback_months=roc_lookback_months,
        top_n=top_n,
        require_positive_roc=require_positive_roc,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
