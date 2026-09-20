"""Strategy: 9/30 EMA/WMA trend-pullback, slope-confirmed variant.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-176):
Per quantifiedstrategies.com's "9/30 Trading Strategy" article
(https://www.quantifiedstrategies.com/9-30-trading-strategy/, originally
developed by Mike Burns), a 9-period EMA and 30-period WMA define a trend
"pullback zone". The source discloses two fully-quantified backtest
variants: (1) a plain crossover, and (2) a slope-confirmed version --
bullish trend defined as 9-EMA > 30-WMA AND the 30-WMA itself sloping
upward; long while both hold, flat otherwise. The source's own SPY backtest
of variant 2 found CAGR 4.5% vs buy-and-hold's 9.2%, invested ~60% of the
time -- modest but not obviously an edge on SPY alone; this is tested here
across QQQ/SPY/crypto and vol regimes as this repo's grid methodology
differs from the source's simple full-sample backtest. Distinct from every
other EMA-crossover entry in this repo (those all compare EMA vs EMA, not
the WMA-slope-confirmed EMA/WMA construction here).

Signal logic
------------
- fast EMA (default 9) of close.
- slow WMA (default 30, linearly-weighted moving average) of close.
- WMA slope = wma - wma.shift(slope_lookback) (default lookback=1 bar,
  i.e. WMA rising vs. the prior bar).
- Long (position=1) whenever fast_EMA > slow_WMA AND slow_WMA is sloping
  upward (slope > 0).
- Flat (position=0) otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series
        {0,1} position series aligned to price_df.index.
    generate_returns(price_df, **params) -> pd.Series
        Position-weighted daily returns (position shifted by 1 day to avoid
        look-ahead bias), no transaction costs applied here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wma(series: pd.Series, window: int) -> pd.Series:
    weights = np.arange(1, window + 1, dtype=float)

    def _wavg(x: np.ndarray) -> float:
        return float(np.dot(x, weights) / weights.sum())

    return series.rolling(window).apply(_wavg, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 5,
    slow_window: int = 40,
    slope_lookback: int = 1,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fast_ema = close.ewm(span=fast_window, adjust=False).mean()
    slow_wma = _wma(close, slow_window)
    slope = slow_wma - slow_wma.shift(slope_lookback)

    long_cond = (fast_ema > slow_wma) & (slope > 0)
    position = long_cond.fillna(False).astype(int)

    warmup = slow_window + slope_lookback
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
