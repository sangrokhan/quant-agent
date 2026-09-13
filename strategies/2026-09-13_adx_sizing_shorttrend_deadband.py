"""Strategy: SMA(short trend_window) directional trend gate with continuous
ADX (Average Directional Index) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-13-092):
ADX (J. Welles Wilder, 1978): derived from smoothed +DI/-DI directional
movement, bounded [0, 100], measuring TREND STRENGTH regardless of
direction (ADX>25 = strong trend, ADX<20 = weak/ranging market -- this
repo's own well-established formula, used in 10+ prior ADX entries, all as
a binary threshold FILTER gating some other entry signal, e.g.
"ADX>threshold AND close>SMA"). This iteration instead uses ADX as a
CONTINUOUS SIZING dial directly: exposure = clip(base_exposure +
adx_sensitivity*((adx-adx_reference)/adx_reference), 0, leverage_cap)
within an SMA(trend_window) uptrend gate -- scale exposure UP as trend
strength (ADX) rises above its reference level (confident, strongly
trending market worth leaning into), scale DOWN as ADX falls (weak/choppy
trend, even though the SMA gate is nominally still long). Fundamentally
distinct from every other sizing-dial indicator tested this cron trigger
(%B/Aroon/WilliamsR/CMO/UO/RVI/StochRSI/MFI/CMF/VZO): all of those measure
DIRECTIONAL momentum or money-flow bias; ADX measures TREND CONVICTION
irrespective of direction, so this sizing dial answers "how much should I
lean into the SMA gate's direction call" rather than "which direction does
the oscillator itself point." First ADX-as-continuous-sizing strategy in
this repo.

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


def _adx(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """Average Directional Index, bounded [0, 100]."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prior_close = close.shift(1)

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    tr = pd.concat(
        [
            high - low,
            (high - prior_close).abs(),
            (low - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    plus_di = 100.0 * plus_dm.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean() / atr.replace(0, np.nan)
    minus_di = 100.0 * minus_dm.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean() / atr.replace(0, np.nan)

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    return adx.clip(lower=0.0, upper=100.0)


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
    adx_reference: float = 25.0,
    base_exposure: float = 0.8,
    adx_sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    adx = _adx(df, window=adx_window)

    raw_exposure = base_exposure + adx_sensitivity * ((adx - adx_reference) / adx_reference)
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    adx_window: int = 14,
    adx_reference: float = 25.0,
    base_exposure: float = 0.8,
    adx_sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        adx_window=adx_window,
        adx_reference=adx_reference,
        base_exposure=base_exposure,
        adx_sensitivity=adx_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
