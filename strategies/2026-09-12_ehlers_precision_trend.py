"""Strategy: Ehlers Precision Trend Analysis (dual 3-pole highpass difference),
trough/peak turning-point entry-exit.

Hypothesis (see knowledge_base id 2026-09-12-171):
Per John Ehlers' "Precision Trend Analysis" (TASC Aug/Sep 2024 Traders' Tips),
transcribed in full C code at https://financial-hacker.com/ehlers-precision-
trend-analysis/: a 3-pole highpass filter (`HighPass3`, a spectral-analysis
construction with pole angle f=1.414*pi/Length) is applied to price at two
different lengths (Length1 > Length2); their DIFFERENCE is Ehlers' own
"Trend" line, designed to track the underlying price trend with near-zero
lag (unlike SMA/WMA/EMA, which the source explicitly says are "too laggy").
A derived `TROC` (trend rate-of-change, the bar-to-bar change of Trend,
scaled by Length2/(2*pi)) captures the trend's own momentum/slope. The
source's blog comment thread explicitly states the intended trading rule:
"Normally you enter and exit at the valleys and peaks of a trend line" --
i.e. TROC crossing from negative to positive marks a trend trough (buy),
and TROC crossing from positive to negative marks a trend peak (sell).

Operationalized here as: long entry when TROC crosses from <=0 to >0
(Trend line making a local trough, turning up); exit when TROC crosses
from >=0 to <0 (Trend line making a local peak, turning down), or a
max_hold_days time-stop as this repo's standard backstop.

First Ehlers Precision Trend / dual-highpass-difference strategy in this
repo -- distinct from every other Ehlers-family entry already tested
(Instantaneous Trendline, Cyber Cycle, Even Better Sinewave, Voss
Predictive Filter, Deviation-Scaled MA/Oscillator, Trendflex, Roofing
Filter, Correlation Cycle, SuperSmoother-as-baseline) via its unique
2-pole-angle 3-pole-highpass DIFFERENCE-OF-TWO-LENGTHS construction and
turning-point (peak/valley) entry logic rather than a zero-line/signal-line
crossover.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _highpass3(data: pd.Series, length: int) -> pd.Series:
    """Ehlers' 3-pole highpass filter (per TASC Aug/Sep 2024 formula).

    HP[0] = c1*(Data[0] - 2*Data[1] + Data[2]) + c2*HP[1] + c3*HP[2]
    where f = 1.414*pi/length, a1 = exp(-f), c2 = 2*a1*cos(f/2),
    c3 = -a1^2, c1 = (1+c2-c3)/4.
    """
    f = 1.414 * math.pi / length
    a1 = math.exp(-f)
    c2 = 2.0 * a1 * math.cos(f / 2.0)
    c3 = -a1 * a1
    c1 = (1.0 + c2 - c3) / 4.0

    values = data.values.astype(float)
    n = len(values)
    hp = np.zeros(n)
    for i in range(n):
        d0 = values[i]
        d1 = values[i - 1] if i >= 1 else values[i]
        d2 = values[i - 2] if i >= 2 else values[i]
        hp1 = hp[i - 1] if i >= 1 else 0.0
        hp2 = hp[i - 2] if i >= 2 else 0.0
        hp[i] = c1 * (d0 - 2.0 * d1 + d2) + c2 * hp1 + c3 * hp2
    return pd.Series(hp, index=data.index)


def _precision_trend(close: pd.Series, length1: int, length2: int):
    hp1 = _highpass3(close, length1)
    hp2 = _highpass3(close, length2)
    trend = hp1 - hp2
    troc = (length2 / (2.0 * math.pi)) * trend.diff()
    return trend, troc


def generate_signals(
    price_df: pd.DataFrame,
    length1: int = 250,
    length2: int = 40,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    _, troc = _precision_trend(close, length1, length2)

    trough = (troc > 0) & (troc.shift(1) <= 0)
    peak = (troc < 0) & (troc.shift(1) >= 0)
    trough = trough.fillna(False)
    peak = peak.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(peak.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(trough.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    length1: int = 250,
    length2: int = 40,
    max_hold_days: int = 40,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs here)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        length1=length1,
        length2=length2,
        max_hold_days=max_hold_days,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    return strat_returns
