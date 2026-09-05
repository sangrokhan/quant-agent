"""Strategy: Ehlers Even Better Sinewave (EBSW) zero-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl):
John Ehlers' Even Better Sinewave (EBSW, "Cycle Analytics for Traders",
2013) high-pass filters price at a chosen `duration` to drop slow trend
content, applies a 2-pole SuperSmoother with `smooth_period` critical
period to strip fast noise, then normalizes a 3-bar average of the result
by the square root of its own recent average power -- confining the output
to roughly -1..+1. Per LuxAlgo's Even-Better Sinewave library page
(https://www.luxalgo.com/library/indicator/even-better-sinewave/): "Zero
crosses: the swing-timing events while the market is cycling -- alerted in
both directions." Long entry on EBSW crossing above zero (a leading
swing-turn-up signal, since the wave leads price turns per Ehlers' design
intent); exit on the opposite cross or a max_hold_days time-stop.

First Even-Better-Sinewave strategy in this repo -- distinct from the
already-tested classic MESA Sine Wave (2026-09-05-069, homodyne-
discriminator Sine/LeadSine PAIR crossover) since EBSW is a single-line
construction (high-pass + SuperSmoother + power normalization) with no
homodyne discriminator or dominant-cycle-period estimation, a materially
different signal-processing pipeline.

Signal logic
------------
- High-pass filter (2-pole, cutoff at `duration` bars) applied to close.
- 2-pole SuperSmoother (critical period `smooth_period`) applied to the
  high-passed series.
- Wave[t] = 3-bar SMA of the smoothed series.
- Power[t] = 3-bar SMA of Wave[t]^2 (average recent power).
- EBSW[t] = Wave[t] / sqrt(Power[t])  (normalized, roughly bounded -1..+1).
- Long entry: EBSW crosses from <=0 to >0.
- Exit: EBSW crosses back below 0, or a max_hold_days time-stop.

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


def _high_pass_filter(price: np.ndarray, duration: int) -> np.ndarray:
    """Ehlers 2-pole high-pass filter with cutoff period = duration."""
    n = len(price)
    hp = np.zeros(n)
    alpha1 = (math.cos(0.707 * 2 * math.pi / duration) + math.sin(0.707 * 2 * math.pi / duration) - 1) / math.cos(0.707 * 2 * math.pi / duration)
    for t in range(n):
        if t < 2:
            hp[t] = 0.0
            continue
        hp[t] = (
            (1 - alpha1 / 2) ** 2 * (price[t] - 2 * price[t - 1] + price[t - 2])
            + 2 * (1 - alpha1) * hp[t - 1]
            - (1 - alpha1) ** 2 * hp[t - 2]
        )
    return hp


def _supersmoother(price: np.ndarray, period: int) -> np.ndarray:
    """Ehlers 2-pole SuperSmoother filter."""
    n = len(price)
    filt = np.zeros(n)
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


def _ebsw(close: pd.Series, duration: int = 40, smooth_period: int = 10) -> pd.Series:
    price = close.to_numpy(dtype=float)
    n = len(price)

    hp = _high_pass_filter(price, duration)
    smoothed = _supersmoother(hp, smooth_period)

    wave = np.zeros(n)
    power = np.zeros(n)
    ebsw = np.full(n, np.nan)
    for t in range(n):
        if t < 3:
            continue
        wave[t] = (smoothed[t] + smoothed[t - 1] + smoothed[t - 2]) / 3.0
        power[t] = (smoothed[t] ** 2 + smoothed[t - 1] ** 2 + smoothed[t - 2] ** 2) / 3.0
        if power[t] > 0:
            ebsw[t] = wave[t] / math.sqrt(power[t])
        else:
            ebsw[t] = 0.0

    return pd.Series(ebsw, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    duration: int = 40,
    smooth_period: int = 10,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ebsw = _ebsw(close, duration=duration, smooth_period=smooth_period)
    long_trigger = (ebsw > 0) & (ebsw.shift(1) <= 0)
    exit_trigger = (ebsw <= 0) & (ebsw.shift(1) > 0)

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
    duration: int = 40,
    smooth_period: int = 10,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    position = generate_signals(
        df, duration=duration, smooth_period=smooth_period, max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns.name = "strategy_returns"
    return strat_returns
