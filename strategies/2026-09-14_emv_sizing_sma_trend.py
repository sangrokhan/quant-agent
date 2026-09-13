"""Strategy: SMA(trend_window) directional gate with continuous Ease of
Movement (EMV, Richard Arms) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-106):
Ease of Movement (Richard W. Arms Jr.): Distance Moved = midpoint(t) -
midpoint(t-1) where midpoint = (High+Low)/2; Box Ratio = (Volume/1e8) /
(High-Low); EMV = Distance Moved / Box Ratio, conventionally smoothed with a
14-period SMA. Formula confirmed via chartschool.stockcharts.com (browser_exec
navigation, web_extract blocked by ddgs-only backend). Repo has one prior EMV
entry (2026-09-04-115): binary threshold-crossover ENTRY signal, accepted
QQQ+SPY only (10-day EMV, 200-day trend filter, max_hold_days=10), crypto
decisively rejected. This iteration reframes EMV as a CONTINUOUS SIZING dial
(the "unbounded indicator -> rolling z-score -> tanh squash" fix pattern that
worked for RWI-diff/EFI/VZO earlier this cron trigger, since raw EMV's scale
drifts with volume level and range just like EFI) within an SMA(trend_window)
uptrend gate, distinct from the fixed-threshold binary version already
tested.

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


def _emv_zscore_signal(
    df: pd.DataFrame, emv_sma_span: int = 14, zscore_window: int = 100
) -> pd.Series:
    """tanh(rolling z-score of SMA-smoothed Ease of Movement), bounded
    [-1, 1]. Normalizes for the fact that raw EMV = distance_moved /
    (volume/high_low_range) has no fixed scale across symbols/time periods."""
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    midpoint = (high + low) / 2.0
    distance_moved = midpoint.diff()
    hl_range = (high - low).replace(0, np.nan)
    box_ratio = (volume / 1e8) / hl_range
    raw_emv = distance_moved / box_ratio.replace(0, np.nan)
    raw_emv = raw_emv.replace([np.inf, -np.inf], np.nan)

    smoothed_emv = raw_emv.rolling(emv_sma_span).mean()

    rolling_mean = smoothed_emv.rolling(zscore_window).mean()
    rolling_std = smoothed_emv.rolling(zscore_window).std().replace(0, np.nan)
    zscore = (smoothed_emv - rolling_mean) / rolling_std

    return np.tanh(zscore)


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
    emv_sma_span: int = 14,
    emv_zscore_window: int = 100,
    base_exposure: float = 0.5,
    emv_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.28,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    emv_signal = _emv_zscore_signal(
        df, emv_sma_span=emv_sma_span, zscore_window=emv_zscore_window
    )

    raw_exposure = base_exposure + emv_sensitivity * emv_signal
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    emv_sma_span: int = 14,
    emv_zscore_window: int = 100,
    base_exposure: float = 0.5,
    emv_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.28,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        emv_sma_span=emv_sma_span,
        emv_zscore_window=emv_zscore_window,
        base_exposure=base_exposure,
        emv_sensitivity=emv_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
