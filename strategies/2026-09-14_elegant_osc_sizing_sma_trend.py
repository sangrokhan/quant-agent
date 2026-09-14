"""Strategy: SMA(trend_window) directional gate with continuous Ehlers
Elegant Oscillator (Inverse Fisher Transform) sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Ehlers Elegant Oscillator (Inverse Fisher Transform), per John F. Ehlers'
TASC February 2022 article, reproduced at
https://financial-hacker.com/the-inverse-fisher-transform/ (already
verified with fully-disclosed C code by this repo's prior strategy
strategies/2026-09-12_elegant_oscillator_meanrev.py; re-used here without
a fresh fetch since the exact formula was already confirmed and logged
this repo):
    deriv[t]      = price[t] - price[t-2]
    rms[t]        = sqrt(mean(deriv[t-length+1..t]^2))
    norm_deriv[t] = deriv[t] / rms[t]
    ift(x)        = (exp(2x) - 1) / (exp(2x) + 1)   -- naturally [-1,+1]
    EO[t]         = SuperSmoother(ift(norm_deriv), smooth_length)[t]
The Inverse Fisher Transform construction guarantees EO stays in [-1,+1]
by design (unlike a raw z-score oscillator that needs an extra tanh-squash
step). This repo's only prior Elegant Oscillator entry (2026-09-12-XXX,
id contains "185" per strategies_index) used EO as a MEAN-REVERSION peak/
valley-threshold ENTRY trigger (accepted SPY only, QQQ rejected on
parameter sensitivity, crypto rejected decisively). This iteration instead
reframes EO as a CONTINUOUS SIZING dial within an SMA(trend_window)
uptrend gate -- same reframing pattern that has repeatedly rescued
binary-only bounded oscillators elsewhere in this repo (BOP, CHOP, VZO,
Vortex-diff-ratio, TSI, RMI, SMI, STARC, Firefly this same cron trigger).
Economic rationale: EO's normalized 2-bar price derivative captures
short-term directional acceleration; using its already-bounded value
directly as a sizing dial (rather than thresholding for discrete entries)
lets exposure track the strength/persistence of that acceleration
continuously within an established uptrend, rather than only reacting to
isolated peak/valley extremes. First Elegant-Oscillator continuous-sizing
variant, and first TREND-FOLLOWING (rather than mean-reversion) use of
this indicator in this repo.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
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


def _elegant_oscillator(close: pd.Series, length: int, smooth_length: int) -> pd.Series:
    deriv = (close - close.shift(2)).fillna(0.0)
    rms = np.sqrt((deriv ** 2).rolling(length, min_periods=5).mean())
    rms = rms.replace(0, np.nan)
    norm_deriv = (deriv / rms).fillna(0.0).clip(-10, 10)

    ift = (np.exp(2 * norm_deriv) - 1) / (np.exp(2 * norm_deriv) + 1)
    eo = _super_smoother(ift, smooth_length)
    return eo


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
    smooth_length: int = 20,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    EO is already naturally bounded [-1,+1] by the Inverse Fisher
    Transform construction -- used directly as a sizing dial (no extra
    z-score/tanh-squash needed), within an SMA(trend_window) uptrend gate.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    eo = _elegant_oscillator(close, length, smooth_length)
    dial = eo.clip(lower=-1.0, upper=1.0)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    length: int = 20,
    smooth_length: int = 20,
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
        smooth_length=smooth_length,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
