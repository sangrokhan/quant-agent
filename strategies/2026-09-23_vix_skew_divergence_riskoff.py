"""Strategy: VIX-SKEW divergence crash-risk-off filter (long-only overlay).

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Per TradingView's "VIX - SKEW Divergence" open-source indicator description
(https://www.tradingview.com/script/uRF1KArk-VIX-SKEW-Divergence/, by
valpatrad, visited this iteration): "When the SKEW rises over a certain
level (~140/150), that means investors are hedging their exposure with
options, because they are worried about an incoming market crash... If
that happens when the VIX is very low and apparently there is no
uncertainty, this can warn of a sudden change in direction of the market...
an increasing divergence often anticipates a sharp fall of leading stock
indexes, usually within two to four months."

This is a first-time VIX-SKEW DIVERGENCE strategy in this repo -- distinct
from the single prior standalone SKEW entry (2026-09-05-029, a rolling
z-score of SKEW alone vs its own history, no VIX cross-reference). The
mechanism here specifically requires the SIMULTANEOUS combination of
elevated SKEW (source's disclosed ~140-150 threshold) AND low VIX (the
"apparently there is no uncertainty" condition) -- a genuinely different
two-variable divergence construction, not a single-variable threshold.

Applied as a long-only risk-off OVERLAY on top of a simple SMA trend-
following signal: go flat (exit any long position) whenever the divergence
condition is active (SKEW >= skew_threshold AND VIX <= vix_threshold),
since the source's own framing is a crash-warning/de-risking signal, not a
short-entry trigger (this repo's SAFETY.md prohibits real short-selling
complexity beyond simple long/flat). Otherwise, trade the underlying
SMA(trend_window) trend-following signal normally.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import sys
import os

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_macro_series(idx: pd.DatetimeIndex, ticker: str) -> pd.Series:
    """Fetch a daily macro index close and align (ffill) onto the target index."""
    from loaders import load_equity

    start = idx.min() - pd.Timedelta(days=30)
    end = idx.max() + pd.Timedelta(days=2)
    df = load_equity(ticker, start.to_pydatetime(), end.to_pydatetime())
    df = _prep(df)
    close = df["close"]

    by_date = close.copy()
    by_date.index = by_date.index.normalize()
    by_date = by_date[~by_date.index.duplicated(keep="last")]

    target_dates = idx.normalize()
    aligned = by_date.reindex(target_dates).ffill()
    aligned.index = idx
    return aligned


def generate_signals(
    price_df: pd.DataFrame,
    skew_threshold: float = 140.0,
    vix_threshold: float = 15.0,
    trend_window: int = 50,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long whenever close > SMA(trend_window) AND NOT (SKEW >= skew_threshold
    AND VIX <= vix_threshold) -- the divergence risk-off condition forces
    flat regardless of the underlying trend signal.
    """
    df = _prep(price_df)
    close = df["close"]

    skew = _get_macro_series(df.index, "^SKEW")
    vix = _get_macro_series(df.index, "^VIX")

    divergence_active = (skew >= skew_threshold) & (vix <= vix_threshold)

    sma = close.rolling(trend_window).mean()
    trend_ok = close > sma

    position = (trend_ok.fillna(False) & (~divergence_active.fillna(False))).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    skew_threshold: float = 140.0,
    vix_threshold: float = 15.0,
    trend_window: int = 50,
) -> pd.Series:
    """Daily strategy returns: position(t-1) * price_return(t) (no lookahead)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        skew_threshold=skew_threshold,
        vix_threshold=vix_threshold,
        trend_window=trend_window,
    )
    price_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(float) * price_returns
    return strat_returns
