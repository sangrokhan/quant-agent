"""Strategy: Triple EMA crossover with alignment confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-070):
Per HowToTrade's Triple Moving Average Crossover article: three EMAs
(recommended 10/30/50) confirm trend direction. Long entry when the
fast(10) EMA crosses above the slow(50) EMA AND the medium(30) EMA sits
between them in bullish alignment (fast > medium > long) at the moment of
the cross, confirming a genuine trend shift rather than a noisy touch.
Exit when close crosses below the medium EMA (source's stated
trailing-stop/mean-reversion-zone role for the medium EMA). Distinct from
GMMA (2026-09-04-062, two CLUSTERS of 6 EMAs each using spread/expansion)
and every dual-MA crossover already tested since this uses exactly THREE
individual EMAs with an alignment-confirmation requirement.

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


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 10,
    medium_window: int = 30,
    slow_window: int = 50,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fast_ema = close.ewm(span=fast_window, adjust=False).mean()
    medium_ema = close.ewm(span=medium_window, adjust=False).mean()
    slow_ema = close.ewm(span=slow_window, adjust=False).mean()

    cross_up = (fast_ema > slow_ema) & (fast_ema.shift(1) <= slow_ema.shift(1))
    bullish_alignment = (fast_ema > medium_ema) & (medium_ema > slow_ema)

    entry_signal = cross_up & bullish_alignment
    exit_signal = close < medium_ema

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
