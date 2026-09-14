"""Strategy: SMA(trend_window) directional gate with continuous Percentage
Volume Oscillator (PVO) sizing overlay + deadband, leverage-cap-aware for
crypto from the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
The Percentage Volume Oscillator (PVO) is the PPO/MACD construction applied
to VOLUME instead of price: PVO = 100*(EMA(fast_span,volume) -
EMA(slow_span,volume)) / EMA(slow_span,volume). Only tested in this repo as
a binary signal-line-crossover entry (2026-09-05-075, ACCEPTED QQQ -- the
only prior PVO entry). This iteration re-tests it as a CONTINUOUS SIZING
dial: since PVO is a %-spread of volume EMAs it is not naturally bounded
(volume shocks can push it well beyond +/-100), so it is rolling
z-scored and tanh-squashed to [-1,+1] before use as an exposure dial within
the SMA(trend_window) uptrend gate -- the same normalization pattern
already validated this cron trigger for other unbounded oscillators
(TRIX-114, CFO-112, Qstick-108, Force Index-105).

Source: same PVO formula as 2026-09-05-075
(https://mangrovedeveloper.ai trading-signals reference); only the *use*
(continuous sizing dial vs. binary crossover) is new.

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


def _pvo(df: pd.DataFrame, fast_span: int, slow_span: int) -> pd.Series:
    volume = df["volume"]
    ema_fast = volume.ewm(span=fast_span, adjust=False).mean()
    ema_slow = volume.ewm(span=slow_span, adjust=False).mean()
    pvo = 100.0 * (ema_fast - ema_slow) / ema_slow.replace(0.0, np.nan)
    return pvo.fillna(0.0)


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
    fast_span: int = 12,
    slow_span: int = 26,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    PVO is rolling z-scored (zscore_window) then tanh-squashed into [-1,+1]
    before being used as a sizing dial within the SMA(trend_window)
    uptrend gate.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    pvo = _pvo(df, fast_span, slow_span)
    pvo_mean = pvo.rolling(zscore_window).mean()
    pvo_std = pvo.rolling(zscore_window).std().replace(0.0, np.nan)
    pvo_z = ((pvo - pvo_mean) / pvo_std).fillna(0.0)
    pvo_dial = np.tanh(pvo_z)

    raw_exposure = base_exposure + sensitivity * pvo_dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    fast_span: int = 12,
    slow_span: int = 26,
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
        fast_span=fast_span,
        slow_span=slow_span,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
