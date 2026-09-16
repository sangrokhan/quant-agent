"""Strategy: Rainbow Moving Average "perfect bullish order" trend-alignment
gate, long-only.

Hypothesis (grounded in Step 2 research this iteration):
Per https://www.quantifiedstrategies.com/rainbow-moving-average/ (visited
this iteration): the Rainbow Moving Average is a cascade of SMAs where the
first layer is an `n`-period SMA of close, and each subsequent layer is an
`n`-period SMA of the *preceding layer* (typically ~10 layers), each
assigned a rainbow color for visual smoothing progression. Source's own
disclosed interpretation: "when the early layer (shorter-period) MAs stay
above the subsequent layer (longer-period) MAs and keep rising further away
from the latter, the market is in an uptrend" -- i.e. a "perfect bullish
order" alignment (price > layer1 > layer2 > ... > layerN) signals trend
strength, and "the closer they are together, the weaker the trend."
Implemented long-only: hold position while the full cascade is in strict
perfect bullish order (close > layer1 > layer2 > ... > layerN), flat
otherwise -- directly encoding the source's own alignment-based trend
read rather than a simple single-MA crossover.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _rainbow_layers(close: pd.Series, period: int, num_layers: int) -> list[pd.Series]:
    layers = []
    current = close
    for _ in range(num_layers):
        current = current.rolling(period, min_periods=period // 2).mean()
        layers.append(current)
    return layers


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 9,
    num_layers: int = 10,
) -> pd.Series:
    """Return a 0/1 position series.

    Long-only: hold while close and all Rainbow MA layers are in strict
    perfect bullish order (close > layer1 > layer2 > ... > layerN), per the
    source's own "early layers above and diverging from later layers =
    uptrend" interpretation. Flat otherwise (no perfect-order alignment).
    """
    df = _prep(price_df)
    close = df["close"]

    layers = _rainbow_layers(close, period, num_layers)
    values = [close] + layers

    aligned = pd.Series(True, index=close.index)
    for i in range(len(values) - 1):
        aligned = aligned & (values[i] > values[i + 1])

    position = aligned.fillna(False).astype(float)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    period: int = 9,
    num_layers: int = 10,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, period=period, num_layers=num_layers)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
