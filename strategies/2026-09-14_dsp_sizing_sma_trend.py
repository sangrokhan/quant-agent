"""Strategy: SMA(trend_window) directional gate with continuous Detrended
Synthetic Price (DSP, Ehlers-style) sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Detrended Synthetic Price (DSP, Ehlers-style), per AlphaX Trading's DSP
dictionary entry (formula already fully confirmed and reused verbatim
from this repo's existing accepted strategy
strategies/2026-09-09_dsp_zerocross_itl_slope.py, no fresh web fetch
needed this sub-step): DSP = typical_price - Instantaneous Trendline (ITL,
an Ehlers-style recursive high-pass/low-pass filter pair extracting a
smoothed trend component). This repo's only prior DSP-zero-cross entry
(2026-09-09-076) used DSP's zero-crossing (plus an ITL-slope confirmation
and a stagnation filter) as a binary ENTRY trigger (accepted QQQ-only,
SPY/crypto rejected). This iteration instead reframes the raw DSP value
as a CONTINUOUS SIZING dial: rolling z-scored and tanh-squashed to
[-1,+1] (since DSP is unbounded, a raw price-minus-trendline deviation) --
the same "unbounded diff -> z-score -> tanh" reframing pattern already
used for TCF and Precision Trend earlier this same cron trigger -- within
an SMA(trend_window) uptrend gate. Economic rationale: DSP measures how
far the (typical) price currently sits above/below its own smoothed
Instantaneous Trendline; a large positive DSP signals price running
strongly ahead of its own smoothed trend (momentum extension), warranting
larger exposure within an established uptrend, while a near-zero DSP
signals price is hugging its trendline (low conviction) even while
nominally above the SMA filter. First DSP continuous-sizing variant.

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


def _instantaneous_trendline(price: pd.Series, filter_period: int) -> pd.Series:
    alpha = 2.0 / (filter_period + 1.0)
    n = len(price)
    itl = [None] * n
    p = price.values
    for i in range(n):
        if i < 2:
            itl[i] = p[i]
        else:
            itl[i] = (
                (alpha - alpha ** 2 / 4.0) * p[i]
                + 0.5 * alpha ** 2 * p[i - 1]
                - (alpha - 0.75 * alpha ** 2) * p[i - 2]
                + 2.0 * (1.0 - alpha) * itl[i - 1]
                - (1.0 - alpha) ** 2 * itl[i - 2]
            )
    return pd.Series(itl, index=price.index, dtype=float)


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
    filter_period: int = 20,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    DSP (typical_price - Instantaneous Trendline, unbounded) is rolling
    z-scored over `zscore_window` bars and tanh-squashed to [-1,+1] before
    use as a sizing dial, within an SMA(trend_window) uptrend gate.
    """
    df = _prep(price_df)
    close = df["close"]
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0

    trend_long = close > close.rolling(trend_window).mean()

    itl = _instantaneous_trendline(typical_price, filter_period)
    dsp = typical_price - itl

    roll_mean = dsp.rolling(zscore_window).mean()
    roll_std = dsp.rolling(zscore_window).std()
    zscore = (dsp - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    filter_period: int = 20,
    zscore_window: int = 100,
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
        filter_period=filter_period,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
