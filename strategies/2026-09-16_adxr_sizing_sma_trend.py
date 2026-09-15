"""Strategy: SMA(trend_window) directional gate with continuous ADXR
(Average Directional Movement Index Rating) trend-conviction sizing
overlay + deadband, leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-16-054, this cron trigger):
ADXR (Wilder's Average Directional Movement Index Rating): ADXR[t] =
(ADX[t] + ADX[t-n]) / 2, a further-smoothed/rated version of ADX itself
(n periods = the ADX period by convention). This repo already has ADX
tested as a continuous trend-conviction sizing dial (id 2026-09-13-092,
accepted QQQ+SPY, rejected crypto) and ADXR tested as a discrete
threshold-crossing entry (id 2026-09-07-013, rejected). This iteration
applies the same continuous-sizing-dial construction validated for plain
ADX to its smoothed sibling ADXR, testing whether the extra smoothing
(averaging ADX against its own n-bars-ago value) reduces whipsaw/turnover
relative to plain ADX enough to also work for crypto (where plain ADX-dial
was rejected) or whether the two behave identically since ADXR is a
literal 2-point moving average of ADX.

Construction (continuous sizing dial): ADXR itself (already bounded
[0,100], measures trend conviction regardless of direction) rescaled to
[0,1] and used directly as a continuous sizing dial (no z-score needed,
same "direct rescale" pattern already used for plain ADX) inside an
SMA(trend_window) uptrend gate (for directional bias, since ADXR/ADX
measure conviction not direction) with a deadband to cut turnover.

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


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    """Wilder's Average Directional Index (Wilder-smoothed via an
    exponential moving average with alpha=1/window, the standard
    approximation of Wilder's original smoothing).
    """
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_dm = pd.Series(plus_dm, index=high.index)
    minus_dm = pd.Series(minus_dm, index=high.index)

    prior_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prior_close).abs(),
            (low - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / window, adjust=False).mean()
    plus_di = 100.0 * plus_dm.ewm(alpha=1.0 / window, adjust=False).mean() / atr.replace(0.0, np.nan)
    minus_di = 100.0 * minus_dm.ewm(alpha=1.0 / window, adjust=False).mean() / atr.replace(0.0, np.nan)

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    adx = dx.ewm(alpha=1.0 / window, adjust=False).mean()
    return adx


def _adxr(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    """ADXR = (ADX[t] + ADX[t-window]) / 2, Wilder's "rating" smoothing."""
    adx = _adx(high, low, close, window)
    adxr = (adx + adx.shift(window)) / 2.0
    return adxr


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
    adx_window: int = 14,
    adxr_cap: float = 50.0,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    ADXR (bounded [0,100], direct rescale by `adxr_cap`) is used as a
    trend-conviction sizing dial, gated by an SMA(trend_window) uptrend
    filter.
    """
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    adxr = _adxr(high, low, close, adx_window)
    dial = (adxr / adxr_cap).clip(lower=0.0, upper=1.0).fillna(0.0)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    adx_window: int = 14,
    adxr_cap: float = 50.0,
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
        adx_window=adx_window,
        adxr_cap=adxr_cap,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
