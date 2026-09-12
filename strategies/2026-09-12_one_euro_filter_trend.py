"""Strategy: Ehlers One Euro Filter trend-following crossover.

Hypothesis (see knowledge_base entry): per John F. Ehlers' TASC article
(reproduced at https://financial-hacker.com/the-one-euro-filter/), the "One
Euro Filter" is an adaptive low-lag smoother whose cutoff period WIDENS
(more smoothing) when price is calm and NARROWS (less lag, tracks price
faster) when price moves quickly -- the opposite adaptation direction of
most adaptive moving averages (which usually speed up in trends and slow
down when choppy, e.g. KAMA/AMA). We hypothesize this distinct adaptation
behavior makes it a good trend-following baseline: long when price closes
above the filter (an established, adaptively-smoothed uptrend), flat
otherwise.

Algorithm (fully disclosed by source, EasyLanguage->pseudocode):
    alpha_dx = 2*pi / (4*pi + 10)
    smoothed_dx[t] = alpha_dx*(price[t]-price[t-1]) + (1-alpha_dx)*smoothed_dx[t-1]
    cutoff[t] = period_min + factor * abs(smoothed_dx[t])
    alpha[t] = 2*pi / (4*pi + cutoff[t])
    filter[t] = alpha[t]*price[t] + (1-alpha[t])*filter[t-1]

Long-only adaptation: long when close > filter, flat when close <= filter.

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


def _one_euro_filter(price: pd.Series, period_min: float, factor: float) -> pd.Series:
    vals = price.to_numpy(dtype=float)
    n = len(vals)
    smoothed_dx = np.zeros(n)
    filt = np.zeros(n)
    alpha_dx = 2 * np.pi / (4 * np.pi + 10)

    filt[0] = vals[0]
    smoothed_dx[0] = 0.0
    for i in range(1, n):
        delta = vals[i] - vals[i - 1]
        smoothed_dx[i] = alpha_dx * delta + (1 - alpha_dx) * smoothed_dx[i - 1]
        cutoff = period_min + factor * abs(smoothed_dx[i])
        alpha = 2 * np.pi / (4 * np.pi + cutoff)
        filt[i] = alpha * vals[i] + (1 - alpha) * filt[i - 1]
    return pd.Series(filt, index=price.index)


def generate_signals(
    price_df: pd.DataFrame,
    period_min: float = 20.0,
    factor: float = 50.0,
) -> pd.Series:
    """Long while close > One Euro Filter, flat otherwise."""
    df = _prep(price_df)
    close = df["close"]

    filt = _one_euro_filter(close, period_min, factor)
    position = (close > filt).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
