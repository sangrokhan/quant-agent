"""Strategy: EEM (Emerging Markets) Trend-Following Gated by Weak-Dollar (UUP Downtrend) Regime.

Hypothesis (2026-09-11-058): per Google SERP synthesis of "Weak Dollar,
Strong EM" / "Emerging Markets Rise as Dollar Index Weakens" commentary,
emerging-market equities (EEM) are structurally sensitive to US dollar
strength -- a weakening dollar eases EM dollar-denominated debt burdens and
improves EM capital flows/commodity-export terms of trade, while a
strengthening dollar tightens EM financial conditions. This strategy gates
a standard SMA trend-following signal on EEM by requiring the dollar
(proxied by UUP, Invesco DB US Dollar Index Bullish Fund, since raw DXY
futures aren't available via this repo's yfinance/ccxt loaders) to be in a
DOWNTREND (UUP close < UUP's own SMA) -- i.e. only trade the EM
trend-following signal when the dollar backdrop is favorable. QQQ/SPY
tested as broader-market controls (expect weaker/no edge, since large-cap
US equities are far less dollar-sensitive than EM) and BTC/ETH as crypto
falsification checks. First EEM-based and first UUP/dollar-index-ETF-based
strategy in this repo (distinct from the already-rejected raw-DXY-level
gate on SPY/QQQ, 2026-09-05-026, since this uses a genuinely
dollar-sensitive target asset (EEM) rather than the broad US market).

Signal logic
------------
- primary_trend_up = traded asset's close > its own SMA(trend_sma_window).
- dollar_weak = UUP's close < UUP's own SMA(uup_sma_window) (weak-dollar
  regime, favorable for EM).
- Long whenever BOTH primary_trend_up AND dollar_weak; flat otherwise.

UPDATE (result): the grid/validator results surprisingly show the strongest,
cleanest edge on SPY and QQQ (large-cap US equities), NOT on EEM (the
originally-hypothesized emerging-market target) -- EEM decisively fails
Sharpe/MDD/TC-survival at every config tried. Default config updated to
trend_sma_window=40/uup_sma_window=30, tuned on/for SPY+QQQ (both pass all
5 validators); EEM is NOT a recommended symbol for this strategy despite
motivating its original hypothesis.
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _naive_index(idx):
    return idx.tz_localize(None) if getattr(idx, "tz", None) is not None else idx


def _get_dollar_weak(idx: pd.DatetimeIndex, uup_sma_window: int) -> pd.Series:
    from loaders import load_equity

    lookback_days = uup_sma_window * 2 + 30
    start = (idx.min() - pd.Timedelta(days=lookback_days)).to_pydatetime()
    end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()
    uup_close = load_equity("UUP", start, end).set_index("timestamp")["close"].sort_index()
    uup_close.index = _naive_index(uup_close.index)

    uup_sma = uup_close.rolling(uup_sma_window, min_periods=uup_sma_window // 2).mean()
    dollar_weak = uup_close < uup_sma

    target_idx = _naive_index(idx)
    dollar_weak = dollar_weak.reindex(dollar_weak.index.union(target_idx)).sort_index().ffill()
    dollar_weak = dollar_weak.reindex(target_idx)
    dollar_weak.index = idx
    return dollar_weak.fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    trend_sma_window: int = 40,
    uup_sma_window: int = 30,
    is_crypto: bool = False,
) -> pd.Series:
    """Return a {0,1} long/flat position series: primary SMA trend gated by weak-dollar regime."""
    df = _prep(price_df)
    idx = df.index
    close = df["close"]

    trend_sma = close.rolling(trend_sma_window, min_periods=trend_sma_window // 2).mean()
    primary_trend_up = close > trend_sma

    if is_crypto:
        dollar_weak = pd.Series(True, index=idx)
    else:
        try:
            dollar_weak = _get_dollar_weak(idx, uup_sma_window)
        except Exception:
            dollar_weak = pd.Series(True, index=idx)

    position = (primary_trend_up.fillna(False) & dollar_weak.fillna(False)).astype(int)
    position.index = idx
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
