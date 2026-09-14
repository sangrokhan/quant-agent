"""Strategy: SMA(trend_window) directional gate with continuous Ehlers
Roofing Filter sizing overlay + deadband, leverage-cap-aware for crypto
from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
John Ehlers' Roofing Filter (2-pole high-pass filter strips slow
trend/drift longer than hp_period bars, then a 2-pole SuperSmoother
low-pass filter strips fast noise shorter than lp_period bars, TASC 2013),
formula already fully confirmed and reused verbatim from this repo's
existing entries strategies/2026-09-05_roofing_filter_signal_crossover.py
and strategies/2026-09-12_ehlers_roofing_filter_signalcross.py (per
https://theindicatorlab.com/reviews/ehlers-roofing-filter/, no fresh web
fetch needed this sub-step). Both prior repo entries used RF-crosses-its-
own-3-period-SMA-signal-line as a BINARY entry trigger with a 200-EMA
trend filter, gated by max_hold_days/trailing exits -- both REJECTED. This
iteration instead reframes the Roofing Filter's own output (a zero-
centered, cycle-bandpassed oscillator, naturally unbounded but well-
behaved) as a CONTINUOUS SIZING dial: rolling z-scored and tanh-squashed
to [-1,+1] within an SMA(trend_window) uptrend gate -- the same "unbounded
diff -> z-score -> tanh" reframing pattern already used successfully for
TCF, Precision Trend, DSP, Voss, WAE, and VQI earlier this cron trigger.
First Ehlers Roofing Filter continuous-sizing variant.

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


def _roofing_filter(close: pd.Series, hp_period: int, lp_period: int) -> pd.Series:
    """Ehlers 2-pole high-pass -> SuperSmoother low-pass Roofing Filter."""
    vals = close.to_numpy(dtype=float)
    n = len(vals)

    alpha1 = (math.cos(2 * math.pi / hp_period) + math.sin(2 * math.pi / hp_period) - 1) / math.cos(
        2 * math.pi / hp_period
    )
    hp = np.zeros(n)
    for i in range(2, n):
        hp[i] = (
            (1 - alpha1 / 2) ** 2 * (vals[i] - 2 * vals[i - 1] + vals[i - 2])
            + 2 * (1 - alpha1) * hp[i - 1]
            - (1 - alpha1) ** 2 * hp[i - 2]
        )

    a1 = math.exp(-1.414 * math.pi / lp_period)
    b1 = 2 * a1 * math.cos(1.414 * math.pi / lp_period)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3

    rf = np.zeros(n)
    for i in range(2, n):
        rf[i] = c1 * (hp[i] + hp[i - 1]) / 2 + c2 * rf[i - 1] + c3 * rf[i - 2]

    return pd.Series(rf, index=close.index)


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
    hp_period: int = 48,
    lp_period: int = 12,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Roofing Filter output is rolling-z-scored over `zscore_window` bars and
    tanh-squashed to [-1,+1] before use as a sizing dial, within an
    SMA(trend_window) uptrend gate.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    rf = _roofing_filter(close, hp_period, lp_period)

    roll_mean = rf.rolling(zscore_window).mean()
    roll_std = rf.rolling(zscore_window).std()
    zscore = (rf - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    hp_period: int = 48,
    lp_period: int = 12,
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
        hp_period=hp_period,
        lp_period=lp_period,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
