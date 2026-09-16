"""Strategy: Schaff Trend Cycle (STC, Doug Schaff) oversold/overbought
crossover, long-only.

Hypothesis (grounded in Step 2 research this iteration):
Per https://howtotrade.com/indicators/schaff-trend-cycle/ (visited this
iteration): STC = 100 * (MACD - %K(MACD)) / (%D(MACD) - %K(MACD)), where
MACD = EMA(close, short_length) - EMA(close, long_length) (Schaff's
defaults: short_length=23, long_length=50), and %K(MACD)/%D(MACD) are a
10-period Stochastic %K/%D computed on the MACD series itself (not on
price) -- STC layers a Stochastic normalization on top of MACD to react
faster to trend cycle turns while staying bounded in [0,100].
Source's own disclosed rule: "when the STC indicator's signal line crosses
above the 75 mark, it indicates overbought... potential sell signal" and
"as the signal line goes below the 25 threshold... oversold condition...
consider initiating a long position." Implemented long-only: enter when STC
crosses up through oversold_level (25) from below, exit when STC crosses
down through overbought_level (75) from above -- the source's own disclosed
levels, held via hysteresis in between (avoids flipping on every STC wiggle
within the 25-75 "trend formation" band the source itself describes).

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


def _stochastic(series: pd.Series, k_period: int) -> pd.Series:
    lo = series.rolling(k_period, min_periods=k_period // 2).min()
    hi = series.rolling(k_period, min_periods=k_period // 2).max()
    rng = (hi - lo).replace(0.0, np.nan)
    pct_k = 100 * (series - lo) / rng
    return pct_k.fillna(50.0)


def _stc(
    close: pd.Series,
    short_length: int,
    long_length: int,
    k_period: int,
    d_period: int,
) -> pd.Series:
    ema1 = close.ewm(span=short_length, adjust=False).mean()
    ema2 = close.ewm(span=long_length, adjust=False).mean()
    macd = ema1 - ema2

    pct_k = _stochastic(macd, k_period)
    pct_d = pct_k.rolling(d_period, min_periods=d_period // 2).mean().fillna(50.0)

    denom = (pct_d - pct_k).replace(0.0, np.nan)
    stc = 100 * (macd - pct_k) / denom
    stc = stc.clip(lower=0, upper=100).fillna(50.0)
    return stc


def generate_signals(
    price_df: pd.DataFrame,
    short_length: int = 23,
    long_length: int = 50,
    k_period: int = 10,
    d_period: int = 3,
    oversold_level: float = 25.0,
    overbought_level: float = 75.0,
) -> pd.Series:
    """Return a 0/1 position series.

    Long-only: enter when STC crosses up through `oversold_level`, exit when
    STC crosses down through `overbought_level` -- source's own disclosed
    levels, held via hysteresis between the two thresholds.
    """
    df = _prep(price_df)
    close = df["close"]

    stc = _stc(close, short_length, long_length, k_period, d_period)
    stc_arr = stc.to_numpy()

    position = np.zeros(len(close), dtype=float)
    held = 0.0
    prev = 50.0
    for i, val in enumerate(stc_arr):
        if held == 0.0:
            if prev < oversold_level <= val:
                held = 1.0
        else:
            if prev > overbought_level >= val:
                held = 0.0
        position[i] = held
        prev = val

    return pd.Series(position, index=close.index)


def generate_returns(
    price_df: pd.DataFrame,
    short_length: int = 23,
    long_length: int = 50,
    k_period: int = 10,
    d_period: int = 3,
    oversold_level: float = 25.0,
    overbought_level: float = 75.0,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        short_length=short_length,
        long_length=long_length,
        k_period=k_period,
        d_period=d_period,
        oversold_level=oversold_level,
        overbought_level=overbought_level,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
