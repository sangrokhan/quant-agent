"""Strategy: Ehlers 3-pole Butterworth low-pass filter crossing its own
lagged trigger line.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-020):
Per FMZ's "Ehlers Three-Pole Butterworth Filter Crossover Trend
Quantitative Trading Strategy" (https://www.fmz.com/lang/en/strategy/498394):
a 3-pole Butterworth LOW-PASS filter (John Ehlers, "Cybernetic Analysis for
Stocks and Futures", 2004) smooths price; a lagged "trigger" version of that
same filter line is compared against it -- filter crossing above trigger
signals a long entry (uptrend), filter crossing below trigger signals exit.
This repo has 2 prior Ehlers Precision Trend entries (2026-09-12-171,
2026-09-14-192) but those use a dual-length HIGHPASS filter DIFFERENCE
turning-point construction, and the SuperSmoother entries
(2026-09-10-021/2026-09-17-088) use a 2-pole low-pass filter with a
slope+price-above-line trigger -- neither tests this specific 3-pole
low-pass-filter-vs-its-own-lagged-trigger-line crossover mechanism.

Signal logic
------------
- Standard Ehlers 3-pole Butterworth low-pass filter coefficients:
    a1 = exp(-pi / period)
    b1 = 2 * a1 * cos(1.738 * pi / period)
    c1 = a1^2
    coef2 = b1 + c1
    coef3 = -(c1 + b1 * c1)
    coef4 = c1^2
    coef1 = 1 - coef2 - coef3 - coef4
    Filt[t] = coef1*(price[t]+2*price[t-1]+price[t-2])/4
              + coef2*Filt[t-1] + coef3*Filt[t-2] + coef4*Filt[t-3]
- Trigger[t] = Filt[t - trigger_lag] (a lagged copy of the same filter line,
  Ehlers' own standard "Trigger" construction for filter-based crossovers).
- Entry (long): Filt crosses above Trigger.
- Exit: Filt crosses below Trigger, OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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


def _butterworth_3pole(price: pd.Series, period: int) -> pd.Series:
    a1 = math.exp(-math.pi / period)
    b1 = 2.0 * a1 * math.cos(1.738 * math.pi / period)
    c1 = a1 ** 2
    coef2 = b1 + c1
    coef3 = -(c1 + b1 * c1)
    coef4 = c1 ** 2
    coef1 = 1.0 - coef2 - coef3 - coef4

    p = price.values
    n = len(p)
    filt = np.zeros(n)
    for i in range(n):
        p0 = p[i]
        p1 = p[i - 1] if i >= 1 else p[i]
        p2 = p[i - 2] if i >= 2 else p[i]
        f1 = filt[i - 1] if i >= 1 else 0.0
        f2 = filt[i - 2] if i >= 2 else 0.0
        f3 = filt[i - 3] if i >= 3 else 0.0
        filt[i] = coef1 * (p0 + 2.0 * p1 + p2) / 4.0 + coef2 * f1 + coef3 * f2 + coef4 * f3

    return pd.Series(filt, index=price.index)


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 20,
    trigger_lag: int = 2,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    filt = _butterworth_3pole(close, period)
    trigger = filt.shift(trigger_lag)

    above = filt > trigger
    prev_above = above.shift(1).fillna(False)
    cross_up = above & (~prev_above)

    below = filt < trigger
    prev_below = below.shift(1).fillna(True)
    cross_down = below & (~prev_below)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]):
                in_position = True
                entry_idx = i
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
