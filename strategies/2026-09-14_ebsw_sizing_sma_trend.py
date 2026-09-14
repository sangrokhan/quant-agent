"""Strategy: SMA(trend_window) directional gate with continuous Ehlers Even
Better Sinewave (EBSW) sizing overlay + deadband, leverage-cap-aware for
crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
John Ehlers' Even Better Sinewave (EBSW, "Cycle Analytics for Traders",
2013), per LuxAlgo's Even-Better Sinewave library page (formula already
fully confirmed and reused verbatim from this repo's existing accepted
strategy strategies/2026-09-06_ehlers_ebsw_zerocross.py, no fresh web
fetch needed this sub-step): price is high-pass filtered at a chosen
`duration` to drop slow trend content, a 2-pole SuperSmoother with
`smooth_period` critical period strips fast noise, then a 3-bar average
of the result is normalized by the square root of its own recent average
power -- confining the output to naturally roughly [-1,+1]. This repo's
only prior EBSW entry (2026-09-06-117) used EBSW's zero-line crossing as
a binary ENTRY trigger (rejected on all symbols: equity Sharpe fail, SPY
also TC-survival fail, crypto 0/36). This iteration reframes EBSW as a
CONTINUOUS SIZING dial (direct rescale, already bounded, no z-score/tanh
needed) within an SMA(trend_window) uptrend gate -- the same reframing
pattern that rescued Firefly Oscillator, Elegant Oscillator, VoRSI, CTM,
and Trendflex (also an Ehlers-family power-normalized oscillator) earlier
this same cron trigger. Economic rationale: while EBSW's own zero-cross
timing signal wasn't a strong standalone entry trigger, its
power-normalized cycle-swing reading may still carry useful CONTINUOUS
information about swing strength/direction that a binary threshold
discards -- using it as a sizing dial (rather than an entry gate) lets the
SMA trend filter handle direction while EBSW modulates conviction. First
EBSW continuous-sizing variant.

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
    duration: int = 40,
    smooth_period: int = 10,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    EBSW (already power-normalized to roughly [-1,+1]) is clipped and used
    directly as a sizing dial, within an SMA(trend_window) uptrend gate.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    ebsw = _ebsw(close, duration=duration, smooth_period=smooth_period)
    dial = ebsw.fillna(0.0).clip(lower=-1.0, upper=1.0)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    duration: int = 40,
    smooth_period: int = 10,
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
        duration=duration,
        smooth_period=smooth_period,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
