"""Strategy: Zero-Lag EMA (ZLEMA) dual crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-066):
Per Google AI-overview + ArrowAlgo/StockGro synthesis: ZLEMA de-lags price
by extrapolating via a lag-period momentum correction (lag=(period-1)/2,
de_lagged = 2*price - price.shift(lag)) BEFORE applying a standard EMA --
distinct construction from every prior MA in this repo (HMA nests WMAs,
KAMA adapts via Efficiency Ratio). Dual-ZLEMA crossover: fast
ZLEMA(fast_window) crossing above slow ZLEMA(slow_window) signals a long
entry; exit on the opposite cross.

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


def _zlema(close: pd.Series, period: int) -> pd.Series:
    lag = max(1, (period - 1) // 2)
    de_lagged = 2 * close - close.shift(lag)
    return de_lagged.ewm(span=period, adjust=False).mean()


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 10,
    slow_window: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fast_zlema = _zlema(close, fast_window)
    slow_zlema = _zlema(close, slow_window)

    cross_up = (fast_zlema > slow_zlema) & (fast_zlema.shift(1) <= slow_zlema.shift(1))
    cross_down = (fast_zlema < slow_zlema) & (fast_zlema.shift(1) >= slow_zlema.shift(1))

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df)):
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
