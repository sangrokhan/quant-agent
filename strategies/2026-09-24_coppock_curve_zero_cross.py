"""Strategy: Coppock Curve zero-line crossover, long-only trend-timing.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-012):
Per QuantifiedStrategies.com's "Coppock Curve Strategy: A Simple Long-Term
Market Timing Indicator"
(https://quantifiedstrategies.substack.com/p/coppock-curve-strategy-a-simple-long),
the classic Coppock Curve = WMA(wma_period) of (ROC(roc_long) + ROC(roc_short))
on monthly closes. Source's own disclosed rule: buy on the curve crossing
above zero (momentum turning from bearish to bullish), sell/reduce on the
curve crossing below zero. Source backtested on the S&P 500 monthly since
1960: 13 trades, 100% win ratio, CAGR 6.5% (vs buy-hold 7.5%), MDD -30%
(vs buy-hold -55%) -- a regime/exposure filter more than a frequent-trading
signal. This repo's data/loaders.py provides only daily OHLCV, so the
monthly lookbacks (roc_long=14 months, roc_short=11 months, wma_period=10
months) are converted to trading-day-equivalent defaults (~21 trading
days/month: roc_long=294d, roc_short=231d, wma_period=210d) and left as
tunable parameters for the grid to explore around that conversion. First
Coppock-Curve-family strategy in this repo (zero prior "Coppock" matches in
strategies_index.jsonl before this entry).

Signal logic
------------
- ROC(roc_long) + ROC(roc_short) on close (percent rate-of-change).
- Coppock = WMA(wma_period) of that sum.
- Long entry: Coppock crosses from <=0 to >0.
- Exit (flat): Coppock crosses from >0 to <=0.
- No other filter -- faithful to the source's own simple zero-line-cross
  rule (a regime/exposure gate, not a fast oscillator).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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


def _wma(series: pd.Series, period: int) -> pd.Series:
    weights = np.arange(1, period + 1)
    return series.rolling(period).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )


def generate_signals(
    price_df: pd.DataFrame,
    roc_long: int = 294,
    roc_short: int = 231,
    wma_period: int = 210,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    roc_l = close.pct_change(roc_long) * 100
    roc_s = close.pct_change(roc_short) * 100
    coppock = _wma(roc_l + roc_s, wma_period)

    above_zero = coppock > 0
    prev_above = above_zero.shift(1).fillna(False)

    cross_up = above_zero & (~prev_above)
    cross_down = (~above_zero) & prev_above

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if pd.isna(coppock.iloc[i]):
            position.iloc[i] = 0
            continue
        if in_position:
            if bool(cross_down.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]):
                in_position = True
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
