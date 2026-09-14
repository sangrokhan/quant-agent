"""Strategy: SMA(trend_window) directional gate with continuous Volatility
Quality Index (VQI) sizing overlay + deadband, leverage-cap-aware for
crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Volatility Quality Index (VQI, Thomas Stridsman): Bar Range = True Range;
Weighted Volatility = Bar Range * sign(Close-Open); VQI Raw =
EMA(Weighted Volatility, vqi_length); VQI Smoothed = EMA(VQI Raw,
smoothing_length). Formula already fully confirmed in this repo's 2 prior
VQI entries (2026-09-08-028 streak-confirmation binary trigger, QQQ Sharpe
0.941 near-miss; 2026-09-08-043 vol-regime-gated follow-up). Both prior
entries used VQI Smoothed's directional STREAK (N consecutive up/down bars)
as a binary trigger. This iteration instead reframes VQI Smoothed itself
(a signed, unbounded EMA-of-signed-true-range series) as a CONTINUOUS
SIZING dial: rolling z-scored and tanh-squashed to [-1,+1] within an
SMA(trend_window) uptrend gate -- the same "unbounded diff -> z-score ->
tanh" pattern already used for TCF, Precision Trend, DSP, Voss, and WAE
earlier this cron trigger. Directly addresses the near-miss nature of
2026-09-08-028 (full-sample Sharpe 0.941, everything else passed) by
smoothing exposure continuously rather than requiring a discrete N-bar
streak, which should reduce whipsaw at streak-count boundaries. First VQI
continuous-sizing variant.

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


def _vqi_smoothed(df: pd.DataFrame, vqi_length: int, smoothing_length: int) -> pd.Series:
    """VQI Smoothed: EMA(EMA(True Range * sign(Close-Open), vqi_length), smoothing_length)."""
    high, low, close, open_ = df["high"], df["low"], df["close"], df["open"]
    prior_close = close.shift(1)
    true_range = pd.concat(
        [
            (high - low),
            (high - prior_close).abs(),
            (low - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    sign = np.sign(close - open_)
    weighted_vol = true_range * sign

    vqi_raw = weighted_vol.ewm(span=vqi_length, adjust=False).mean()
    vqi_smoothed = vqi_raw.ewm(span=smoothing_length, adjust=False).mean()
    return vqi_smoothed


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
    vqi_length: int = 14,
    smoothing_length: int = 5,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    VQI Smoothed is rolling-z-scored over `zscore_window` bars and
    tanh-squashed to [-1,+1] before use as a sizing dial, within an
    SMA(trend_window) uptrend gate.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    vqi = _vqi_smoothed(df, vqi_length, smoothing_length).fillna(0.0)

    roll_mean = vqi.rolling(zscore_window).mean()
    roll_std = vqi.rolling(zscore_window).std()
    zscore = (vqi - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    vqi_length: int = 14,
    smoothing_length: int = 5,
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
        vqi_length=vqi_length,
        smoothing_length=smoothing_length,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
