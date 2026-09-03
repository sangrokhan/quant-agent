"""Strategy: Guppy Multiple Moving Average (GMMA) crossover with expansion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-062):
Per Capital.com's GMMA guide (Daryl Guppy): the GMMA uses two clusters of
6 EMAs each -- short-term (3,5,8,10,12,15) representing trader
activity, and long-term (30,35,40,45,50,60) representing investor
behavior -- distinct from every prior single/dual-MA crossover already
tested in this repo since it uses ribbon SPREAD/expansion between two
groups of 6 EMAs as a trend-strength confirmation rather than a single
fast/slow pair. Concrete crossover rule: long entry when the average of
the short-term EMA group crosses above the average of the long-term EMA
group AND then expands apart (ribbon divergence confirming trend
strength, per the source's explicit "must expand apart" caveat); exit on
the reverse crossover.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd

SHORT_PERIODS_DEFAULT = (3, 5, 8, 10, 12, 15)
LONG_PERIODS_DEFAULT = (30, 35, 40, 45, 50, 60)


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _group_avg_ema(close: pd.Series, periods: tuple[int, ...]) -> pd.Series:
    emas = [close.ewm(span=p, adjust=False).mean() for p in periods]
    return sum(emas) / len(emas)


def generate_signals(
    price_df: pd.DataFrame,
    expansion_lookback: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    short_avg = _group_avg_ema(close, SHORT_PERIODS_DEFAULT)
    long_avg = _group_avg_ema(close, LONG_PERIODS_DEFAULT)
    spread = short_avg - long_avg

    cross_up = (short_avg > long_avg) & (short_avg.shift(1) <= long_avg.shift(1))
    cross_down = (short_avg < long_avg) & (short_avg.shift(1) >= long_avg.shift(1))

    # Expansion confirmation: spread must be widening over the lookback window.
    expanding = spread > spread.shift(expansion_lookback)

    entry_signal = cross_up & expanding
    exit_signal = cross_down

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
