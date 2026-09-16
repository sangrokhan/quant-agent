"""Strategy: Ehlers Super Smoother slope + price-above-line trend filter,
long-only.

Hypothesis (grounded in Step 2 research this iteration):
Per https://alphax.trading/dictionary/ehlers-super-smoother (visited this
iteration): John Ehlers' Super Smoother is a 2-pole Butterworth recursive
digital filter with minimal lag relative to a standard moving average:

    a1 = exp(-1.414*pi/period)
    b1 = 2*a1*cos(radians(1.414*180/period))
    c2 = b1
    c3 = -a1**2
    c1 = 1 - c2 - c3
    SS[t] = c1*(price[t]+price[t-1])/2 + c2*SS[t-1] + c3*SS[t-2]

Source's own disclosed execution rules: "Enter a long position when the
Super Smoother slope turns positive and price closes above the smoothed
line. Exit long positions when the Super Smoother slope flattens or turns
negative, indicating a loss of momentum." Implemented exactly as disclosed:
long while SS[t] > SS[t-1] (positive slope) AND close > SS[t], flat
otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _super_smoother(price: pd.Series, period: int) -> pd.Series:
    a1 = math.exp(-1.414 * math.pi / period)
    b1 = 2 * a1 * math.cos(math.radians(1.414 * 180.0 / period))
    c2 = b1
    c3 = -(a1 ** 2)
    c1 = 1 - c2 - c3

    price_arr = price.to_numpy()
    n = len(price_arr)
    ss = np.zeros(n)

    for i in range(n):
        if i == 0:
            ss[i] = price_arr[i]
        elif i == 1:
            ss[i] = (price_arr[i] + price_arr[i - 1]) / 2.0
        else:
            ss[i] = (
                c1 * (price_arr[i] + price_arr[i - 1]) / 2.0
                + c2 * ss[i - 1]
                + c3 * ss[i - 2]
            )

    return pd.Series(ss, index=price.index)


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 20,
) -> pd.Series:
    """Return a 0/1 position series.

    Long while the Super Smoother's slope is positive AND close is above
    the smoothed line -- source's own disclosed execution rule.
    """
    df = _prep(price_df)
    close = df["close"]

    ss = _super_smoother(close, period)
    slope_positive = ss.diff() > 0
    above_line = close > ss

    position = (slope_positive & above_line).fillna(False).astype(float)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    period: int = 20,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, period=period)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
