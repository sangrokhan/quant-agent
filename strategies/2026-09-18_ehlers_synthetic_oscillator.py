"""Strategy: John F. Ehlers' Synthetic Oscillator, momentum crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl for this id): Ehlers'
"Synthetic Oscillator" (TASC April 2026, "A Synthetic Oscillator") builds a
phase-based sine waveform tracking the instantaneous dominant cycle of price
(via a bandpass-filtered/normalized quadrature-arctangent measurement), then
demonstrates (per the Wealth-Lab Traders' Tips implementation) a reversion
trading strategy: take the *momentum* (1-bar difference) of a Hann-windowed
smoothing of the oscillator itself, and go long when that momentum crosses
above zero (rising synthetic-cycle phase = trough forming), exit when it
crosses back below zero (peak forming). This is a genuinely novel
oscillator construction not previously tested in this repo (distinct from
prior Ehlers Reversion Index / Reflex / Continuation Index entries, which
use different normalization/filter chains and don't do the arctan-based
adaptive dominant-cycle phase tracking this indicator does).

Source: https://traders.com/Documentation/FEEDbk_docs/2026/04/TradersTips.html
(TradeStation EasyLanguage code + Wealth-Lab C# demonstration strategy,
fetched via browser_exec; both fully disclosed).

Implementation notes
---------------------
The oscillator's construction chains several classic Ehlers recursive
filters (2-pole highpass, 2-pole SuperSmoother lowpass, Hann-windowed FIR,
"UltimateSmoother"), all IIR/FIR filters with a handful of taps/poles, so
they are implemented here with a single bar-by-bar Python loop (vectorized
recursive filters aren't expressible cleanly in pandas rolling ops). This is
fine for daily OHLCV series (thousands of bars, not millions).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def _hann_series(price: np.ndarray, length: int) -> np.ndarray:
    """Ehlers Hann-windowed FIR lowpass filter (per TASC EasyLanguage)."""
    n = len(price)
    out = np.zeros(n)
    weights = np.array([1 - math.cos(2 * math.pi * c / (length + 1)) for c in range(1, length + 1)])
    coef = weights.sum()
    if coef == 0:
        return price.copy()
    for i in range(n):
        acc = 0.0
        for c in range(1, length + 1):
            idx = i - (c - 1)
            if idx < 0:
                continue
            acc += weights[c - 1] * price[idx]
        out[i] = acc / coef
    return out


def _highpass(price: np.ndarray, period: float) -> np.ndarray:
    """Ehlers 2-pole highpass filter."""
    n = len(price)
    out = np.zeros(n)
    a1 = math.exp(-1.414 * math.pi / period)
    b1 = 2 * a1 * math.cos(math.radians(1.414 * 180 / period))
    c2 = b1
    c3 = -a1 * a1
    c1 = (1 + c2 - c3) / 4
    for i in range(n):
        if i >= 4:
            out[i] = (
                c1 * (price[i] - 2 * price[i - 1] + price[i - 2])
                + c2 * out[i - 1]
                + c3 * out[i - 2]
            )
        else:
            out[i] = 0.0
    return out


def _supersmoother(price: np.ndarray, period: float) -> np.ndarray:
    """Ehlers 2-pole SuperSmoother lowpass filter."""
    n = len(price)
    out = np.zeros(n)
    a1 = math.exp(-1.414 * math.pi / period)
    b1 = 2 * a1 * math.cos(math.radians(1.414 * 180 / period))
    c2 = b1
    c3 = -a1 * a1
    c1 = (1 - c2 - c3) / 2  # note: differs slightly per TASC listing variants; use energy-preserving form
    for i in range(n):
        if i >= 4:
            out[i] = c1 * (price[i] + price[i - 1]) + c2 * out[i - 1] + c3 * out[i - 2]
        else:
            out[i] = price[i]
    return out


def _rms(price: np.ndarray, length: int) -> np.ndarray:
    n = len(price)
    out = np.zeros(n)
    for i in range(n):
        lo = max(0, i - length + 1)
        window = price[lo : i + 1]
        if len(window) == 0:
            out[i] = 0.0
            continue
        out[i] = math.sqrt(float(np.mean(window * window)))
    return out


def _ultimate_smoother(price: np.ndarray, period: float) -> np.ndarray:
    """Ehlers UltimateSmoother -- near-zero-lag lowpass filter."""
    n = len(price)
    out = np.zeros(n)
    a1 = math.exp(-1.414 * math.pi / period)
    b1 = 2 * a1 * math.cos(math.radians(1.414 * 180 / period))
    c2 = b1
    c3 = -a1 * a1
    c1 = (1 + c2 - c3) / 4
    for i in range(n):
        if i >= 4:
            out[i] = (
                (1 - c1) * price[i]
                + (2 * c1 - c2) * price[i - 1]
                - (c1 + c3) * price[i - 2]
                + c2 * out[i - 1]
                + c3 * out[i - 2]
            )
        else:
            out[i] = price[i]
    return out


def _synthetic_oscillator(close: np.ndarray, lower_bound: int, upper_bound: int, hann_length: int) -> np.ndarray:
    """Ehlers Synthetic Oscillator (TASC April 2026), per TradeStation EasyLanguage."""
    n = len(close)
    price = _hann_series(close, hann_length)

    hp = _highpass(price, upper_bound)
    lp = _supersmoother(hp, lower_bound)

    rms = _rms(lp, 100)
    real = np.zeros(n)
    for i in range(n):
        real[i] = lp[i] / rms[i] if rms[i] != 0 else 0.0

    roc = np.zeros(n)
    roc[1:] = real[1:] - real[:-1]

    qrms = _rms(roc, 100)
    imag = np.zeros(n)
    for i in range(n):
        imag[i] = roc[i] / qrms[i] if qrms[i] != 0 else 0.0

    mid = math.sqrt(lower_bound * upper_bound)
    hp2 = _highpass(close, mid)
    bp = _ultimate_smoother(hp2, mid)

    dc = np.full(n, mid)
    phase = np.zeros(n)
    synth = np.zeros(n)

    for i in range(n):
        if i >= 1:
            denom = (real[i] - real[i - 1]) * imag[i] - (imag[i] - imag[i - 1]) * real[i]
            if denom != 0:
                dc_val = 6.28 * (real[i] ** 2 + imag[i] ** 2) / denom
            else:
                dc_val = dc[i - 1]
        else:
            dc_val = mid

        if dc_val < lower_bound:
            dc_val = lower_bound
        if dc_val > upper_bound:
            dc_val = upper_bound
        dc[i] = dc_val

        prev_phase = phase[i - 1] if i >= 1 else 0.0
        new_phase = prev_phase + (360.0 / dc_val)

        if i >= 1 and bp[i - 1] <= 0 < bp[i]:
            new_phase = 180.0 / dc_val
        elif i >= 1 and bp[i - 1] >= 0 > bp[i]:
            new_phase = 180.0 + (180.0 / dc_val)

        phase[i] = new_phase
        s = math.sin(math.radians(new_phase))

        prev_synth = synth[i - 1] if i >= 1 else 0.0
        phase_mod = new_phase % 360.0
        if 0 < phase_mod < 90 and s < prev_synth:
            s = prev_synth
        elif 180 < phase_mod < 270 and s > prev_synth:
            s = prev_synth

        synth[i] = s

    return synth


def _compute_signal_raw(
    df: pd.DataFrame,
    lower_bound: int,
    upper_bound: int,
    hann_length: int,
    mom_hann_length: int,
) -> pd.Series:
    close = df["close"].to_numpy(dtype=float)
    synth = _synthetic_oscillator(close, lower_bound, upper_bound, hann_length)
    smooth_synth = _hann_series(synth, mom_hann_length)
    mom = np.zeros(len(smooth_synth))
    mom[1:] = smooth_synth[1:] - smooth_synth[:-1]
    return pd.Series(mom, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    lower_bound: int = 15,
    upper_bound: int = 25,
    hann_length: int = 12,
    mom_hann_length: int = 4,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry when the momentum of the Hann-smoothed Synthetic Oscillator
    crosses above zero; exit on the mirror cross below zero, or after
    max_hold_days (avoid indefinite holds -- this repo's standard pattern).
    """
    df = _prep(price_df)
    mom = _compute_signal_raw(df, lower_bound, upper_bound, hann_length, mom_hann_length)

    cross_up = (mom > 0) & (mom.shift(1) <= 0)
    cross_down = (mom < 0) & (mom.shift(1) >= 0)

    position = np.zeros(len(df))
    in_pos = False
    hold_count = 0
    cu = cross_up.to_numpy()
    cd = cross_down.to_numpy()
    for i in range(len(df)):
        if in_pos:
            hold_count += 1
            if cd[i] or hold_count >= max_hold_days:
                in_pos = False
                hold_count = 0
            else:
                position[i] = 1
        else:
            if cu[i]:
                in_pos = True
                hold_count = 0
                position[i] = 1
    return pd.Series(position, index=df.index, dtype=float)


def generate_returns(
    price_df: pd.DataFrame,
    lower_bound: int = 15,
    upper_bound: int = 25,
    hann_length: int = 12,
    mom_hann_length: int = 4,
    max_hold_days: int = 20,
) -> pd.Series:
    """Daily strategy returns (no transaction costs -- applied separately)."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        hann_length=hann_length,
        mom_hann_length=mom_hann_length,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
