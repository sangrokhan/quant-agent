"""Strategy: Volume Weighted Moving Average (VWMA) dual crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-060):
Per Google search results (Pineify VWMA Strategy Guide, corroborated by
ThinkorSwim's VWMABreakouts): the Volume Weighted Moving Average (VWMA)
weights price by traded volume over a rolling window, distinct from
every other volume-weighted indicator in this repo (all prior ones weight
a MOMENTUM measure by volume; VWMA weights the PRICE AVERAGE itself).
Standard dual-VWMA crossover rule: fast (20-period) VWMA crossing above
slow (50-period) VWMA signals a long entry; exit on the opposite cross.

VWMA formula (standard):
    VWMA_n = sum(close * volume, n) / sum(volume, n)

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


def _vwma(close: pd.Series, volume: pd.Series, window: int) -> pd.Series:
    pv = (close * volume).rolling(window).sum()
    v = volume.rolling(window).sum()
    return pv / v.replace(0, pd.NA)


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 20,
    slow_window: int = 50,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, volume = df["close"], df["volume"]

    fast_vwma = _vwma(close, volume, fast_window)
    slow_vwma = _vwma(close, volume, slow_window)

    entry_signal = (fast_vwma > slow_vwma) & (fast_vwma.shift(1) <= slow_vwma.shift(1))
    exit_signal = (fast_vwma < slow_vwma) & (fast_vwma.shift(1) >= slow_vwma.shift(1))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
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
