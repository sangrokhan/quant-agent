"""Strategy: DEMA (Double Exponential Moving Average) dual crossover, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-079):
DEMA (Patrick Mulloy) = 2*EMA(n) - EMA(EMA(n)), designed to reduce the lag
of a plain EMA by subtracting out a portion of the smoothing delay.
Standard dual-DEMA crossover: fast DEMA crossing above slow DEMA signals a
long entry (momentum shift with reduced lag vs an equivalent dual-EMA
crossover), opposite cross exits. Distinct from TEMA (already tested at
2026-09-04-068, applies EMA three times: 3*EMA1-3*EMA2+EMA3) and ZLEMA
(2026-09-04-066, de-lags via extrapolation before a single EMA) -- DEMA
uses only two EMA applications with a simpler 2x-1x weighting.

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


def _dema(close: pd.Series, span: int) -> pd.Series:
    ema1 = close.ewm(span=span, adjust=False).mean()
    ema2 = ema1.ewm(span=span, adjust=False).mean()
    return 2 * ema1 - ema2


def generate_signals(
    price_df: pd.DataFrame,
    fast_span: int = 10,
    slow_span: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: fast DEMA crosses above slow DEMA.
    Exit: fast DEMA crosses back below slow DEMA.
    """
    df = _prep(price_df)
    close = df["close"]

    fast_dema = _dema(close, fast_span)
    slow_dema = _dema(close, slow_span)

    cross_up = (fast_dema > slow_dema) & (fast_dema.shift(1) <= slow_dema.shift(1))
    cross_down = (fast_dema < slow_dema) & (fast_dema.shift(1) >= slow_dema.shift(1))

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df)):
        if in_position:
            if bool(cross_down.iloc[i]) if not pd.isna(cross_down.iloc[i]) else False:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]) if not pd.isna(cross_up.iloc[i]) else False:
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
