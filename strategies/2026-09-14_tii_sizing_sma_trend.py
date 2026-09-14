"""Strategy: SMA(trend_window) directional gate with continuous Trend
Intensity Index (TII) sizing overlay + deadband, leverage-cap-aware for
crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Trend Intensity Index (TII): major_sma = SMA(close, major_period);
deviation = close - major_sma; sdpos = rolling-sum(positive deviations,
minor_period); sdneg = rolling-sum(|negative deviations|, minor_period);
TII = 100 * sdpos / (sdpos + sdneg), bounded [0,100], centered at 50 (no
trend bias) -- reused verbatim from this repo's own 3 prior confirmed TII
entries (2026-09-04_tii_midline_cross.py,
2026-09-05_tii_extreme_threshold_sma_filter.py,
2026-09-08_tii_trend_intensity_breakout.py), all of which use TII as a
BINARY midline-cross / extreme-threshold / breakout ENTRY trigger. None
used TII's own continuous magnitude as a SIZING dial. This iteration
reframes TII as a CONTINUOUS SIZING dial: center at 50 (TII-50)/50 to map
[0,100]->[-1,1] directly (TII is already bounded, so no z-score/tanh
normalization stage is needed, unlike unbounded oscillators used earlier
this cron trigger), used as a sizing multiplier within an
SMA(trend_window) uptrend gate, deadband to cut turnover, leverage_cap for
crypto. First Trend Intensity Index continuous-sizing variant in this
repo.

Source: repo's own prior confirmed formula (2026-09-04/05/08 TII entries);
no new external source needed this iteration -- pure technique variant
on an already-confirmed, bounded oscillator.

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


def _tii(close: pd.Series, major_period: int, minor_period: int) -> pd.Series:
    major_sma = close.rolling(major_period).mean()
    deviation = close - major_sma

    pos_dev = deviation.where(deviation > 0, 0.0)
    neg_dev = (-deviation).where(deviation < 0, 0.0)

    sdpos = pos_dev.rolling(minor_period).sum()
    sdneg = neg_dev.rolling(minor_period).sum()

    tii = 100.0 * sdpos / (sdpos + sdneg).replace(0.0, np.nan)
    return tii.fillna(50.0)


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
    major_period: int = 30,
    minor_period: int = 10,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    TII is already bounded [0,100] and centered at 50 -- directly rescale
    to [-1,+1] via (TII-50)/50 without an additional z-score/tanh stage.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    tii = _tii(close, major_period, minor_period)
    dial = ((tii - 50.0) / 50.0).clip(-1.0, 1.0)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    major_period: int = 30,
    minor_period: int = 10,
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
        major_period=major_period,
        minor_period=minor_period,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
