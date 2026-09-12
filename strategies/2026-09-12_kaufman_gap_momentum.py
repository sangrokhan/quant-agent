"""Strategy: Perry Kaufman Gap Momentum (GAPM) rising/falling trend-follow.

Hypothesis (see knowledge_base entry): per Perry Kaufman's TASC 1/24
article, reproduced at
https://financial-hacker.com/the-gap-momentum-system/ (fully disclosed C
code): a rolling ratio of cumulative up-gaps (today's open above
yesterday's close) to cumulative down-gaps (today's open below yesterday's
close) over a `period`-bar window, smoothed by an SMA of length
`signal_period`, tracks whether gap-driven buying or selling pressure is
building. Long while the smoothed GAPM signal is rising (up-gap pressure
increasing relative to down-gap pressure), flat while falling.

Algorithm (fully disclosed by source):
    for each bar i in the trailing `period` window:
        gap = open[i] - close[i-1]
        if gap > 0: up_gaps += gap
        else:       down_gaps += -gap
    gap_ratio = 100 * up_gaps / down_gaps  (1 if down_gaps == 0)
    GAPM = SMA(gap_ratio, signal_period)

Long-only adaptation: long while GAPM[t] > GAPM[t-1] (rising), flat while
GAPM[t] <= GAPM[t-1] (falling), mirroring the source's own `rising()`/
`falling()` entry/exit rule.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _gapm(open_: pd.Series, close: pd.Series, period: int, signal_period: int) -> pd.Series:
    gap = open_ - close.shift(1)
    up_gap = gap.clip(lower=0)
    down_gap = (-gap).clip(lower=0)

    up_sum = up_gap.rolling(period).sum()
    down_sum = down_gap.rolling(period).sum()

    gap_ratio = np.where(down_sum == 0, 1.0, 100.0 * up_sum / down_sum.replace(0, np.nan))
    gap_ratio = pd.Series(gap_ratio, index=open_.index).fillna(1.0)

    gapm = gap_ratio.rolling(signal_period).mean()
    return gapm


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 40,
    signal_period: int = 20,
) -> pd.Series:
    """Long while GAPM signal is rising, flat while falling."""
    df = _prep(price_df)
    open_ = df["open"]
    close = df["close"]

    gapm = _gapm(open_, close, period, signal_period)
    rising = gapm > gapm.shift(1)
    position = rising.fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
