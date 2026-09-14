"""Strategy: SMA(trend_window) directional gate with continuous Ehlers
Trendflex sizing overlay + deadband, leverage-cap-aware for crypto from
the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
John Ehlers' Trendflex indicator (TASC Feb 2020 "Reflex: A New Zero-Lag
Indicator"), per https://www.prorealcode.com/prorealtime-indicators/reflex-and-trendflex-indicators-john-f-ehlers/
(formula already fully confirmed and reused verbatim from this repo's
existing accepted strategy
strategies/2026-09-06_ehlers_trendflex_zerocross.py, no fresh web fetch
needed this sub-step): a SuperSmoother 2-pole low-pass filter is applied
to close; the filter's deviation from each of the last `length` bars is
averaged, then normalized by a recursively-computed mean-square
(MS[t]=0.04*s^2+0.96*MS[t-1], Ehlers' own smoothing constants) so the
oscillator is naturally expressed in standard-deviation units centered
around zero (roughly [-3,+3] in practice, like a z-score). This repo's
only prior Trendflex entry (2026-09-06-112) used a zero-line CROSSOVER as
a binary ENTRY trigger (accepted SPY-only, QQQ near-miss, crypto rejected
decisively). This iteration reframes Trendflex as a CONTINUOUS SIZING dial
(tanh-squashed since the raw value is a z-score-like unbounded-in-theory
quantity) within an SMA(trend_window) uptrend gate -- the same reframing
pattern that rescued Firefly Oscillator, Elegant Oscillator, VoRSI, TCF,
and CTM earlier this same cron trigger. Economic rationale: Trendflex's
near-zero-lag, RMS-normalized measure of the filtered trend's persistence
lets exposure track how strongly (in standard-deviation terms) the
low-lag filtered price has been rising over the lookback window,
continuously rather than only reacting to a single zero-crossing. First
Trendflex continuous-sizing variant.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
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


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    length: int = 20,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Trendflex (already RMS-normalized to a z-score-like scale) is
    tanh-squashed to [-1,+1] and used as a sizing dial, within an
    SMA(trend_window) uptrend gate.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    tf = _trendflex(close, length=length)
    dial = np.tanh(tf.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    length: int = 20,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        length=length,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
