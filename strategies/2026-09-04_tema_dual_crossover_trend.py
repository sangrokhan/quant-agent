"""Strategy: Triple EMA (TEMA) dual crossover with 200-SMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-068):
Per Google AI-overview (PyQuantLab/GoCharting synthesis): TEMA
(Triple Exponential Moving Average) = 3*EMA1 - 3*EMA2 + EMA3 (EMA applied
recursively three times, weighted to cancel lag terms beyond DEMA).
Distinct construction from ZLEMA (de-lag via price extrapolation), HMA
(nested WMAs), and KAMA (Efficiency-Ratio adaptive smoothing) already
tested in this repo. Long entry: fast TEMA(9) crosses above slow TEMA(21)
AND close > SMA(200) macro trend filter; exit on stop-and-reverse (fast
TEMA crosses back below slow TEMA) OR trend invalidation (close closes
below the 200 SMA).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _tema(close: pd.Series, span: int) -> pd.Series:
    ema1 = close.ewm(span=span, adjust=False).mean()
    ema2 = ema1.ewm(span=span, adjust=False).mean()
    ema3 = ema2.ewm(span=span, adjust=False).mean()
    return 3 * ema1 - 3 * ema2 + ema3


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 9,
    slow_window: int = 21,
    trend_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fast_tema = _tema(close, fast_window)
    slow_tema = _tema(close, slow_window)
    trend_sma = close.rolling(trend_window).mean()

    cross_up = (fast_tema > slow_tema) & (fast_tema.shift(1) <= slow_tema.shift(1))
    trend_ok = close > trend_sma

    entry_signal = cross_up & trend_ok
    exit_signal = (fast_tema < slow_tema) | (close < trend_sma)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
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
