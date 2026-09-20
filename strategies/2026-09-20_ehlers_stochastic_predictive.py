"""Strategy: Ehlers Stochastic (Roofing-Filter-smoothed Stochastic),
predictive mode.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-XXX):
Per https://toslc.thinkorswim.com/center/reference/Tech-Indicators/
studies-library/E-F/EhlersStochastic (John F. Ehlers, "Predictive
Indicators For Effective Trading Strategies", TASC January 2014): a
standard %K Stochastic oscillator applied not to raw price but to price
first passed through Ehlers' "Roofing Filter" -- a high-pass filter
(removes slow drift/spectral dilation, cutoff `cutoff_length`, default 48
bars) followed by a SuperSmoother low-pass filter (removes high-frequency
noise, cutoff 10 bars) -- which the source states specifically targets
wave cycles between 10 and 48 bars, discarding both faster noise and
slower trend components before the Stochastic calculation.

The source describes TWO distinct signal modes on the same filtered
Stochastic value:
  - CONVENTIONAL: buy when Stochastic crosses ABOVE the oversold level,
    sell when it crosses BELOW the overbought level (ordinary momentum
    breakout logic).
  - PREDICTIVE: buy when Stochastic crosses BELOW the oversold level,
    sell when it crosses ABOVE the overbought level (the source's own
    novel contribution per its TASC title -- an anticipatory/
    mean-reversion-at-the-extreme signal, entering INTO the extreme
    rather than waiting for it to resolve).

This strategy implements PREDICTIVE mode as the primary/default (the
source's own named contribution, distinguishing this from every plain
stochastic-crossover strategy already in this repo), with `mode` as a
tunable parameter so conventional mode can also be grid-tested. First
Ehlers Roofing-Filter-based Stochastic strategy in this repo -- distinct
from all prior plain/smoothed Stochastic variants via the specific
bandpass (10-48 bar) pre-filtering step, and from all prior Ehlers-family
entries (Instantaneous Trendline, SuperSmoother, Fisher Transform, etc.)
via being a Stochastic-oscillator application rather than a moving-average
or price-transform application of Ehlers' DSP techniques.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1})
    generate_returns(price_df, **params) -> pd.Series
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
    if len(df.index) > 1:
        median_gap = pd.Series(df.index).diff().median()
        if pd.notna(median_gap) and median_gap < pd.Timedelta(hours=20):
            df = df.resample("1D").agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                }
            ).dropna()
    return df


def _roofing_filter(price: np.ndarray, cutoff_length: int, hp_length: int = 10) -> np.ndarray:
    """Ehlers Roofing Filter: a high-pass filter (removes cycles longer
    than `cutoff_length` bars) followed by a 2-pole SuperSmoother low-pass
    filter (removes cycles shorter than `hp_length` bars), passing only
    the [hp_length, cutoff_length] band -- standard Ehlers DSP
    construction used across his TASC articles."""
    n = len(price)
    hp = np.zeros(n)
    filt = np.zeros(n)

    alpha1 = (
        math.cos(0.707 * 2 * math.pi / cutoff_length)
        + math.sin(0.707 * 2 * math.pi / cutoff_length)
        - 1
    ) / math.cos(0.707 * 2 * math.pi / cutoff_length)

    for i in range(2, n):
        if np.isnan(price[i]) or np.isnan(price[i - 1]) or np.isnan(price[i - 2]):
            hp[i] = 0.0
            continue
        hp[i] = (
            (1 - alpha1 / 2) ** 2 * (price[i] - 2 * price[i - 1] + price[i - 2])
            + 2 * (1 - alpha1) * hp[i - 1]
            - (1 - alpha1) ** 2 * hp[i - 2]
        )

    a1 = math.exp(-1.414 * math.pi / hp_length)
    b1 = 2 * a1 * math.cos(1.414 * math.pi / hp_length)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3

    for i in range(2, n):
        filt[i] = c1 * (hp[i] + hp[i - 1]) / 2 + c2 * filt[i - 1] + c3 * filt[i - 2]

    return filt


def _ehlers_stochastic(
    close: pd.Series, length: int, cutoff_length: int, hp_length: int
) -> pd.Series:
    filt = _roofing_filter(close.values.astype(float), cutoff_length, hp_length)
    filt_s = pd.Series(filt, index=close.index)
    lowest = filt_s.rolling(length).min()
    highest = filt_s.rolling(length).max()
    rng = (highest - lowest).replace(0.0, np.nan)
    stoch = 100 * (filt_s - lowest) / rng
    return stoch


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 20,
    cutoff_length: int = 48,
    hp_length: int = 10,
    overbought: float = 70.0,
    oversold: float = 30.0,
    mode: str = "predictive",
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(df)

    stoch = _ehlers_stochastic(close, length, cutoff_length, hp_length)
    stoch_v = stoch.values

    position = np.zeros(n, dtype=int)
    in_pos = False
    for i in range(1, n):
        prev, cur = stoch_v[i - 1], stoch_v[i]
        if np.isnan(prev) or np.isnan(cur):
            position[i] = int(in_pos)
            continue
        if mode == "conventional":
            buy_signal = prev <= oversold and cur > oversold
            sell_signal = prev >= overbought and cur < overbought
        else:  # predictive
            buy_signal = prev >= oversold and cur < oversold
            sell_signal = prev <= overbought and cur > overbought

        if not in_pos and buy_signal:
            in_pos = True
        elif in_pos and sell_signal:
            in_pos = False
        position[i] = int(in_pos)

    return pd.Series(position, index=df.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strategy_ret
