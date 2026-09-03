"""Strategy: Coppock Curve zero-line-cross long-term momentum.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-036):
Per quantifiedstrategies.com's Coppock Curve article, E.S.C. Coppock's 1965
long-term market-timing indicator (originally monthly-bar, 11/14-period ROC
sum smoothed by a 10-period WMA) generates a long entry when it crosses
above zero and an exit when it crosses back below zero, capturing
significant multi-year uptrend swings while filtering out downtrends.

The source's own design is MONTHLY-bar (11/14/10 = months), producing only
12 trades over 63 years on the S&P 500 -- far too few over this repo's
~7.7-year (2019-2026) daily-OHLCV sample to be statistically meaningful if
implemented as true monthly bars. This strategy is deliberately tested at
DAILY bar frequency using the SAME period counts (11, 14, 10) as an explicit
frequency-mismatch stress test (same methodology used for the HMA
5-minute-to-daily frequency change, 2026-09-04-026) -- expecting this to
behave as a much faster/noisier momentum oscillator than Coppock's original
long-term design, since 11/14/10 TRADING DAYS is roughly 2-3 weeks rather
than nearly a year.

Coppock Curve formula (source, standard params roc1=11, roc2=14, wma_window=10):
    ROC(n) = (close / close.shift(n) - 1) * 100
    CoppockCurve = WMA(ROC(close, roc1) + ROC(close, roc2), wma_window)

Signal logic
------------
- Entry (long): Coppock Curve crosses from <= 0 to > 0.
- Exit: Coppock Curve crosses from > 0 to <= 0.
- Flat otherwise; long-only, no shorting.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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
    weights = np.arange(1, window + 1)

    def _weighted(x):
        return np.dot(x, weights) / weights.sum()

    return series.rolling(window).apply(_weighted, raw=True)


def _coppock_curve(close: pd.Series, roc1: int, roc2: int, wma_window: int) -> pd.Series:
    roc_a = (close / close.shift(roc1) - 1.0) * 100.0
    roc_b = (close / close.shift(roc2) - 1.0) * 100.0
    return _wma(roc_a + roc_b, wma_window)


def generate_signals(
    price_df: pd.DataFrame,
    roc1: int = 11,
    roc2: int = 14,
    wma_window: int = 20,
) -> pd.Series:
    # NOTE: default wma_window=20 (not the source's original monthly-design
    # value of 10) is the grid/validator-selected primary config for QQQ
    # (see backtests/2026-09-04_coppock_curve_zeroline.md) -- wma_window=10
    # narrowly fails the 25% MDD ceiling on QQQ full-sample (26.1%), while
    # 20 clears it (22.6%) with only a small Sharpe cost (1.185 -> 1.098).
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    coppock = _coppock_curve(close, roc1, roc2, wma_window)
    above_zero = coppock > 0

    position = above_zero.fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
