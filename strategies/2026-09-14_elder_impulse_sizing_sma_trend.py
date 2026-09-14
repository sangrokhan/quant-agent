"""Strategy: SMA(trend_window) directional gate with continuous Elder
Impulse System sizing overlay + deadband, leverage-cap-aware for crypto
from the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Elder Impulse System (Alexander Elder): a 13-period EMA slope identifies
trend direction, and the MACD(12,26,9) histogram's own slope measures
momentum; the system "paints" green bars when BOTH the EMA and the MACD
histogram are rising (bulls control trend + momentum), red bars when BOTH
are falling, blue bars otherwise (disagreement). Per
https://www.quantifiedstrategies.com/elder-impulse-system/ (visited this
iteration): "The slope of the exponential moving average (EMA) identifies
the trend, while the rise or decline of the MACD histogram measures
momentum... combines trend-following and momentum strategies."

This repo has 1 prior Elder Impulse entry (2026-09-04-125), a BINARY
bar-color-based entry/exit trigger (long on bar turning green, exit when it
stops being green), gated by a higher-timeframe EMA slope filter. This
iteration instead builds a CONTINUOUS SIZING dial from the joint EMA-slope
+ MACD-histogram-slope construction: both slopes are rolling z-score
normalized and averaged into a single [-1, 1]-clipped "impulse strength"
score, which scales exposure within an SMA(trend_window) uptrend gate --
reusing this cron trigger's validated continuous-sizing-dial pattern
(19+ other indicator families tested this way).

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


def _macd_hist(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line - signal_line


def _zscore(series: pd.Series, window: int) -> pd.Series:
    mean = series.rolling(window).mean()
    std = series.rolling(window).std().replace(0, np.nan)
    return ((series - mean) / std).clip(lower=-2.5, upper=2.5)


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
    ema_period: int = 13,
    zscore_window: int = 90,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Impulse strength = average of (z-scored EMA(ema_period) slope) and
    (z-scored MACD-histogram slope), each clipped to [-2.5, 2.5] before
    averaging and rescaling to [-1, 1] by dividing by 2.5.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    ema13 = close.ewm(span=ema_period, adjust=False).mean()
    ema_slope = ema13.diff()
    ema_slope_z = _zscore(ema_slope, zscore_window)

    macd_hist = _macd_hist(close)
    macd_hist_slope = macd_hist.diff()
    macd_slope_z = _zscore(macd_hist_slope, zscore_window)

    impulse_strength = ((ema_slope_z + macd_slope_z) / 2.0) / 2.5
    impulse_strength = impulse_strength.clip(lower=-1.0, upper=1.0)

    raw_exposure = base_exposure + sensitivity * impulse_strength
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ema_period: int = 13,
    zscore_window: int = 90,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        ema_period=ema_period,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
