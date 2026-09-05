"""Strategy: Ehlers Trendflex zero-line crossover trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl):
John Ehlers' Trendflex indicator (TASC Feb 2020 "Reflex: A New Zero-Lag
Indicator") isolates the trend component of price with near-zero lag by
(1) running a SuperSmoother low-pass filter over close, (2) summing the
filter's deviation from each of the last `length` bars, normalized by a
recursively-computed root-mean-square (so the oscillator is expressed in
units of standard deviations, centered around zero), and NOT detrending by
a projected slope (that's the companion "Reflex" indicator, which
synchronizes with cycles instead). Because Trendflex tracks the trend
component with minimal lag, a zero-line crossing (Trendflex > 0 = filtered
price still rising vs `length` bars ago) is Ehlers' own proposed entry
signal (analogous to a fast, low-lag moving-average-slope flip).

Source: https://www.prorealcode.com/prorealtime-indicators/reflex-and-trendflex-indicators-john-f-ehlers/
(full ProRealTime code transcription of Ehlers' original TASC formula).

First Trendflex/Reflex-family strategy in this repo -- distinct from all
prior Ehlers strategies already tested (Fisher Transform, Instantaneous
Trendline, MESA MAMA/FAMA, Laguerre RSI, Roofing Filter, Detrended
Synthetic Price, Ergodic Oscillator) since Trendflex's SuperSmoother +
recursive-RMS-normalization construction and zero-lag design are unique to
this indicator pair.

Signal logic
------------
- SuperSmoother 2-pole filter (Ehlers' standard 2-pole Butterworth-derived
  smoother) applied to close, with cutoff period ~ 0.5*length.
- Trendflex[t] = mean_{k=1..length}(Filt[t] - Filt[t-k]) / sqrt(MS[t]),
  where MS[t] = 0.04*Sum[t]^2 + 0.96*MS[t-1] (recursive mean-square,
  Ehlers' own smoothing constants, hard-coded in the source formula).
- Long entry: Trendflex crosses from <=0 to >0 (filtered trend turning up).
- Exit: Trendflex crosses back below 0, or a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _supersmoother(price: np.ndarray, length: int) -> np.ndarray:
    """Ehlers 2-pole SuperSmoother filter, cutoff period = 0.5*length."""
    n = len(price)
    filt = np.zeros(n)
    period = max(0.5 * length, 2.0)
    a1 = math.exp(-1.414 * math.pi / period)
    b1 = 2.0 * a1 * math.cos(1.414 * math.pi / period)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1.0 - c2 - c3
    for t in range(n):
        if t < 2:
            filt[t] = price[t]
            continue
        filt[t] = c1 * (price[t] + price[t - 1]) / 2.0 + c2 * filt[t - 1] + c3 * filt[t - 2]
    return filt


def _trendflex(close: pd.Series, length: int = 20) -> pd.Series:
    """Ehlers Trendflex oscillator (trend component, zero-lag, normalized)."""
    price = close.to_numpy(dtype=float)
    n = len(price)
    filt = _supersmoother(price, length)

    trendflex = np.full(n, np.nan)
    ms = 0.0
    for t in range(n):
        if t < length:
            continue
        s = 0.0
        for count in range(1, length + 1):
            s += filt[t] - filt[t - count]
        s /= length
        ms = 0.04 * s * s + 0.96 * ms
        if ms > 0:
            trendflex[t] = s / math.sqrt(ms)
        else:
            trendflex[t] = 0.0

    return pd.Series(trendflex, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 20,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    tf = _trendflex(close, length=length)
    long_trigger = (tf > 0) & (tf.shift(1) <= 0)
    exit_trigger = (tf <= 0) & (tf.shift(1) > 0)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trigger.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(long_trigger.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1

    position.name = "position"
    return position


def generate_returns(
    price_df: pd.DataFrame,
    length: int = 20,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    position = generate_signals(df, length=length, max_hold_days=max_hold_days)
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns.name = "strategy_returns"
    return strat_returns
