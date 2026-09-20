"""Strategy: classic 13/48 EMA dual crossover, long-only, no filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-175):
Per quantifiedstrategies.com's "13/48 Trading Strategy" article
(https://www.quantifiedstrategies.com/13-48-trading-strategy/), a 13-period
EMA crossing above a 48-period EMA is a bullish trend signal; crossing below
is bearish. The source's own backtest on the S&P 500 cash index (1960-
present) found it invested ~66% of the time, captured 5.1% CAGR vs. buy-and-
hold's 7.2%, but with a slightly better risk-adjusted return (7.8%) -- i.e.
a plain, unfiltered dual-EMA crossover is not obviously profitable
out-of-the-box but may hold up better on other symbols/asset classes, or as
a baseline control against the many *filtered* EMA-crossover variants
already in this repo (OBV-confirmed, RSI-confirmed, volume-confirmed,
zero-lag EMA, adaptive EMA, etc.) -- this is the plain classic 13/48 with NO
additional filter, testable as a distinct baseline.

Signal logic
------------
- fast EMA (default 13) and slow EMA (default 48) of close.
- Long (position=1) whenever fast EMA > slow EMA.
- Flat (position=0) whenever fast EMA <= slow EMA.
- No additional trend/volatility/volume filter (deliberately, to match the
  source's plain baseline construction).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series
        {0,1} position series aligned to price_df.index.
    generate_returns(price_df, **params) -> pd.Series
        Position-weighted daily returns (position shifted by 1 day to avoid
        look-ahead bias), no transaction costs applied here.
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
    fast_window: int = 13,
    slow_window: int = 48,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fast_ema = close.ewm(span=fast_window, adjust=False).mean()
    slow_ema = close.ewm(span=slow_window, adjust=False).mean()

    position = (fast_ema > slow_ema).astype(int)
    # No signal until both EMAs have enough data to be meaningful.
    warmup = max(fast_window, slow_window)
    position.iloc[:warmup] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
