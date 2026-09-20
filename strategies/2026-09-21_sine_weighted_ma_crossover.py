"""Strategy: Sine-Weighted Moving Average (SWMA) dual crossover, gated by a
longer-term SMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-170):
Per Linn Software's moving-average reference
(https://www.linnsoft.com/techind/moving-averages-ma, freely available),
the Sine-Weighted Moving Average (SWMA) is similar in concept to the
Triangular Moving Average but derives its per-bar weighting factors from a
sine calculation (weight_i proportional to sin(pi*(i+1)/(n+1)) for
i=0..n-1) instead of a linear triangular ramp -- this smoothly up-weights
the middle of the lookback window and tapers both ends, producing a
distinct lag/smoothness tradeoff versus every other MA family already
tested in this repo (SMA/EMA/WMA/Triangular/Hull/KAMA/T3/ALMA/etc, 0 prior
SWMA hits). This strategy tests the standard MA-family pattern already
validated elsewhere in this repo for other MA types: a fast/slow SWMA dual
crossover (fast SWMA crossing above slow SWMA signals a long entry, the
reverse crossing signals exit), gated by a longer SMA(trend_window) trend
filter to avoid trading against the macro trend and reduce whipsaws in
choppy/ranging markets.

Signal logic
------------
- SWMA(n) at bar t = sum_{i=0}^{n-1} w_i * close[t-n+1+i] / sum(w_i), where
  w_i = sin(pi*(i+1)/(n+1)), i=0..n-1 (weights peak at the CENTER of the
  window and taper to near-zero at both ends -- distinct from Triangular
  MA's linear taper).
- Long entry: fast SWMA crosses above slow SWMA AND close > SMA(trend_window).
- Exit: fast SWMA crosses back below slow SWMA, OR close falls below
  SMA(trend_window) (trend invalidation), OR max_hold_days reached.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position series)
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _swma(series: pd.Series, window: int) -> pd.Series:
    weights = np.array([math.sin(math.pi * (i + 1) / (window + 1)) for i in range(window)])
    weights = weights / weights.sum()

    def _wavg(x):
        return np.dot(x, weights)

    return series.rolling(window).apply(_wavg, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 10,
    slow_window: int = 30,
    trend_window: int = 100,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    idx = df.index
    n = len(idx)

    close = df["close"]
    fast_swma = _swma(close, fast_window)
    slow_swma = _swma(close, slow_window)
    trend_sma = close.rolling(trend_window).mean()

    bullish_cross = (fast_swma > slow_swma) & (fast_swma.shift(1) <= slow_swma.shift(1))
    bearish_cross = (fast_swma < slow_swma) & (fast_swma.shift(1) >= slow_swma.shift(1))
    trend_ok = close > trend_sma

    position = pd.Series(0, index=idx, dtype=int)
    in_position = False
    entry_i = -1
    for i in range(n):
        if in_position:
            hold_days = i - entry_i
            exit_signal = bool(bearish_cross.iloc[i]) or not bool(trend_ok.iloc[i]) or hold_days >= max_hold_days
            if exit_signal:
                in_position = False
            else:
                position.iloc[i] = 1
        else:
            if bool(bullish_cross.iloc[i]) and bool(trend_ok.iloc[i]):
                in_position = True
                entry_i = i
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    fast_window: int = 10,
    slow_window: int = 30,
    trend_window: int = 100,
    max_hold_days: int = 60,
) -> pd.Series:
    """Daily strategy returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        fast_window=fast_window,
        slow_window=slow_window,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
