"""Strategy: Aroon Oscillator zero-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-063):
Per RunBacktest's Aroon Oscillator strategy page: Aroon Oscillator =
AroonUp - AroonDown (both computed over a rolling lookback window from
bars-since-highest-high / bars-since-lowest-low). Long entry when the
oscillator crosses above zero (AroonUp > AroonDown, accelerating
bullishness), exit when it crosses back below zero. Distinct from this
repo's prior Aroon-Down-only strategy (2026-09-04-031, absolute-level
thresholds on AroonDown alone) since this uses the AroonUp-AroonDown
DIFFERENCE oscillator with a zero-line-cross rule.

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


def _aroon_up_down(high: pd.Series, low: pd.Series, window: int) -> tuple[pd.Series, pd.Series]:
    def bars_since_max(x):
        return (len(x) - 1) - np.argmax(x.values)

    def bars_since_min(x):
        return (len(x) - 1) - np.argmin(x.values)

    periods_since_high = high.rolling(window + 1).apply(bars_since_max, raw=False)
    periods_since_low = low.rolling(window + 1).apply(bars_since_min, raw=False)

    aroon_up = 100.0 * (window - periods_since_high) / window
    aroon_down = 100.0 * (window - periods_since_low) / window
    return aroon_up, aroon_down


def generate_signals(
    price_df: pd.DataFrame,
    aroon_window: int = 25,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low = df["high"], df["low"]

    aroon_up, aroon_down = _aroon_up_down(high, low, aroon_window)
    oscillator = aroon_up - aroon_down

    cross_up = (oscillator > 0) & (oscillator.shift(1) <= 0)
    cross_down = (oscillator < 0) & (oscillator.shift(1) >= 0)

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
