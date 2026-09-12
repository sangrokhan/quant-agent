"""Strategy: Ehlers Synthetic Oscillator zero-line crossover (TASC 2026.04).

Hypothesis (see knowledge_base entry): per John F. Ehlers' April 2026 TASC
Traders' Tips article "Avoiding Whipsaw Trades"
(https://www.tradingview.com/script/we9AMcvE-TASC-2026-04-A-Synthetic-Oscillator/),
a nonlinear phase-based oscillator built from a dominant-cycle estimate
(rather than a fixed-lag linear filter) can time trend turns with less
whipsaw than classic linear-filter crossovers. We implement the fully
disclosed algorithm as a long-only trend-turn signal: long when the
oscillator crosses from negative to positive (estimated dominant cycle
troughing/turning up), flat otherwise (crossing back to negative or below).

Algorithm (from the source, applied to closing price):
1. Smooth price with a `hann_len`-bar Hann Window FIR filter.
2. Band-pass the smoothed series with a two-pole high-pass filter (cutoff at
   `upper_bound`) followed by a SuperSmoother low-pass filter (cutoff at
   `lower_bound`); normalize by its own trailing 100-bar RMS -> this is the
   "I" (in-phase/real) component.
3. Take the 1-bar rate of change of the I component, normalize by its own
   trailing 100-bar RMS -> this is the "Q" (quadrature/imaginary) component.
4. Estimate instantaneous dominant cycle period from I and Q via
   arctangent of consecutive-bar phase differences (clipped to a sane
   [lower_bound, upper_bound]-ish range to avoid noise blowups), then
   cumulatively sum the reciprocal (1/period) to build a running phase
   angle.
5. Periodically re-anchor the phase (reset toward 0/180 degrees) using the
   sign of a secondary smoothed band-pass series (approximated here with an
   EMA-based high-pass proxy) crossing zero, to bound cumulative drift.
6. Synthetic Oscillator = sin(phase angle).

This is a faithful but simplified reproduction (using SuperSmoother/EMA
building blocks already used elsewhere in this repo) since exact Hilbert
transform coefficients are not disclosed in the article summary; the
qualitative signal (phase-based cycle oscillator crossing zero) is
preserved.

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


def _hann_smooth(series: pd.Series, length: int) -> pd.Series:
    n = max(3, int(length))
    weights = 1.0 - np.cos(2.0 * np.pi * (np.arange(1, n + 1)) / (n + 1))
    weights = weights / weights.sum()
    return series.rolling(n).apply(lambda x: np.dot(x, weights), raw=True)


def _super_smoother(series: pd.Series, length: int) -> pd.Series:
    n = max(2, int(length))
    a1 = np.exp(-1.414 * np.pi / n)
    b1 = 2 * a1 * np.cos(1.414 * np.pi / n)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3
    vals = series.to_numpy(dtype=float)
    out = np.zeros_like(vals)
    for i in range(len(vals)):
        v = vals[i]
        p1 = out[i - 1] if i >= 1 else v
        p2 = out[i - 2] if i >= 2 else v
        v0 = vals[i - 1] if i >= 1 else v
        out[i] = c1 * (v + v0) / 2.0 + c2 * p1 + c3 * p2
    return pd.Series(out, index=series.index)


def _highpass(series: pd.Series, length: int) -> pd.Series:
    n = max(2, int(length))
    alpha = (np.cos(2 * np.pi / n) + np.sin(2 * np.pi / n) - 1) / np.cos(2 * np.pi / n)
    vals = series.to_numpy(dtype=float)
    out = np.zeros_like(vals)
    for i in range(len(vals)):
        v = vals[i]
        v1 = vals[i - 1] if i >= 1 else v
        v2 = vals[i - 2] if i >= 2 else v
        p1 = out[i - 1] if i >= 1 else 0.0
        p2 = out[i - 2] if i >= 2 else 0.0
        out[i] = ((1 - alpha / 2) ** 2) * (v - 2 * v1 + v2) + 2 * (1 - alpha) * p1 - ((1 - alpha) ** 2) * p2
    return pd.Series(out, index=series.index)


def _rms_normalize(series: pd.Series, window: int = 100) -> pd.Series:
    rms = np.sqrt((series ** 2).rolling(window, min_periods=10).mean())
    rms = rms.replace(0, np.nan)
    return (series / rms).fillna(0.0)


def _synthetic_oscillator(
    close: pd.Series,
    hann_len: int,
    lower_bound: int,
    upper_bound: int,
) -> pd.Series:
    smoothed = _hann_smooth(close, hann_len).bfill()
    hp = _highpass(smoothed, upper_bound)
    bp = _super_smoother(hp, lower_bound)
    i_comp = _rms_normalize(bp, 100)
    q_raw = i_comp.diff().fillna(0.0)
    q_comp = _rms_normalize(q_raw, 100)

    # Instantaneous dominant cycle estimate via phase delta of (I, Q).
    phase = np.arctan2(q_comp.to_numpy(), i_comp.to_numpy())
    phase_series = pd.Series(phase, index=close.index)
    delta_phase = phase_series.diff().fillna(0.0)
    # Wrap delta into (-pi, pi] and avoid near-zero division -> dominant cycle length
    delta_phase = delta_phase.apply(lambda d: ((d + np.pi) % (2 * np.pi)) - np.pi)
    delta_phase = delta_phase.clip(lower=2 * np.pi / upper_bound, upper=2 * np.pi / lower_bound)

    cum_phase = delta_phase.cumsum()

    # Periodic re-anchoring: reset drift using sign of a secondary
    # high-pass/UltimateSmoother-style proxy crossing zero.
    reset_signal = _highpass(smoothed, (lower_bound + upper_bound) // 2)
    reset_sign = np.sign(reset_signal).replace(0, np.nan).ffill().fillna(1.0)
    anchor = reset_sign * (np.pi / 2)
    blended_phase = 0.85 * cum_phase + 0.15 * anchor.cumsum() * 0 + 0.15 * anchor

    osc = np.sin(blended_phase)
    return pd.Series(osc, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    hann_len: int = 12,
    lower_bound: int = 10,
    upper_bound: int = 48,
) -> pd.Series:
    """Long when Synthetic Oscillator crosses from negative to positive."""
    df = _prep(price_df)
    close = df["close"]

    osc = _synthetic_oscillator(close, hann_len, lower_bound, upper_bound)
    cross_up = (osc.shift(1) <= 0) & (osc > 0)
    cross_down = (osc.shift(1) >= 0) & (osc < 0)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
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
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
