"""Strategy: SMA(trend_window) directional gate with continuous QQE
(Quantitative Qualitative Estimation, smoothed-RSI-minus-50) sizing
overlay + deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
QQE (Quantitative Qualitative Estimation), per howtotrade.com's QQE
tutorial (already confirmed in this repo's prior QQE entries
2026-09-08-162 and 2026-09-12-160, both rejected binary
crossover/confirmation triggers): smooths RSI with a fast EMA (RSI_MA),
then builds an ATR-of-RSI-delta trailing-band ratchet around it (a
Supertrend/Chandelier-style construction applied to RSI space, not price
space). This repo has 2 prior QQE entries, both binary trigger/confirmation
systems, none accepted. This iteration isolates QQE's underlying smoothed
RSI itself, centered around its 50 midline (RSI_MA - 50), as a CONTINUOUS
SIZING dial: rolling z-scored + tanh-squashed to [-1,1], used as a sizing
multiplier within an SMA(trend_window) uptrend gate, deadband to cut
turnover, leverage_cap for crypto. First QQE continuous-sizing variant.

Source: reused formula/attribution from prior repo research (howtotrade.com
QQE tutorial, already confirmed in 2026-09-08-162); this iteration uses
only the smoothed-RSI component of QQE, not the full ATR-of-RSI trailing
band construction, as a deliberate simplification for the sizing-dial
framing.

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


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


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
    rsi_period: int = 14,
    rsi_smooth: int = 5,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    QQE's smoothed RSI (EMA(RSI(rsi_period), rsi_smooth)), centered around
    its 50 midline, is rolling-z-scored over `zscore_window` bars and
    tanh-squashed to [-1,+1] before use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    rsi = _rsi(close, rsi_period)
    rsi_ma = rsi.ewm(span=rsi_smooth, adjust=False).mean()
    centered = rsi_ma - 50.0

    roll_mean = centered.rolling(zscore_window).mean()
    roll_std = centered.rolling(zscore_window).std()
    zscore = (centered - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    rsi_period: int = 14,
    rsi_smooth: int = 5,
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
        rsi_period=rsi_period,
        rsi_smooth=rsi_smooth,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
