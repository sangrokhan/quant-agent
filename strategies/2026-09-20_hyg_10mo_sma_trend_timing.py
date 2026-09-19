"""Strategy: HYG (high-yield bond ETF) 10-month SMA trend-timing (Yieldstream-style).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-060):
Per Yieldstream's "Trend-following on high-yield bonds"
(https://www.yieldstream.com/blog/11/Trend_following_on_high_yield_bonds,
visited this iteration via browser_exec fallback -- web_search DDGS
backend hit repeated TLS/connection-reset errors this iteration), high-yield
bond market leadership rotates with the economic cycle: capital flows into
high-yield debt when the economy is favorable, and out into safer
Treasuries when conditions weaken. This creates well-defined price trends
in high-yield bond funds. The source's own fully disclosed rule and
backtest (on USAA High-Yield Opportunities, USHYX, 2002-2011): "Buy the
USHYX fund when the monthly closing price rises above its 10-month SMA.
Otherwise, sell it and invest in T-Bills." Reported results: CAGR 11.02%
vs 8.73% buy-and-hold, Sharpe 1.58 vs 0.70, MDD -4.86% vs -31.23%.

This repo already tested HYG's own 200-day SMA as an EXTERNAL GATE on
QQQ/SPY trend-following (2026-09-11-027/028, accepted SPY/QQQ) -- a
fundamentally different use (HYG as a macro regime signal for equities).
This iteration instead trades HYG ITSELF based on its own trend, per the
Yieldstream source's disclosed direct-timing rule: long HYG when its
close is above its own trailing SMA(sma_window) (approximating the
source's 10-month monthly SMA translated to a daily-bar trading_days_per_month
default of 21, i.e. sma_window=210 for ~10 months), flat otherwise
(source's T-Bills allocation approximated here as simply flat/cash, since
this repo doesn't model a risk-free-rate cash leg).

First strategy in this repo to trade HYG directly as the primary asset
using HYG's own trend signal (vs. using it as an external gate).

Source: https://www.yieldstream.com/blog/11/Trend_following_on_high_yield_bonds
(fully disclosed SMA rule and its own backtest stats, on USHYX not HYG --
this repo substitutes HYG, the liquid ETF available via
data/loaders.py::load_equity, as the tradeable high-yield-bond proxy since
USHYX is a mutual fund not reliably available via yfinance).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (position: 1 long/0 flat)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 210,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(sma_window).mean()
    position = (close > sma).astype(int)
    position = position.fillna(0)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
