"""Strategy: SMA(trend_window) directional gate with continuous Elder Force
Index (EFI) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-105):
Elder Force Index (Alexander Elder; formula per DuckDuckGo HTML SERP results
from arrowalgo.com, ta-lib.org, positioned.app, chart-formations.com,
lightningchart.com -- all consistent): EFI = (Close - Prior Close) * Volume,
typically EMA-smoothed (span 13 in Elder's own usage). Combines price change
direction/magnitude with volume participation into a single unbounded money
flow measure. This repo has 5 prior Force Index entries (dual-EMA pullback,
divergence variants), all binary threshold/crossover/divergence ENTRY
triggers; the EMA(13)/EMA(2-3) dual-timeframe pullback variant was accepted
QQQ-only (2026-09-04-049), all others rejected.

Unlike VHF/PFE (natively bounded) or the sign-only VZO/CHOP/ADX family, raw
EFI's magnitude scales with both price volatility and volume level, so it is
NOT usable as a sizing dial without normalization. This iteration
normalizes EFI via a rolling z-score (vs its own trailing distribution) then
squashes with tanh to bounded [-1, 1] -- the same "unbounded indicator ->
squash before sizing" fix that worked for RWI-diff (2026-09-14-104) earlier
this cron trigger -- then uses it as a CONTINUOUS SIZING dial within an
SMA(trend_window) uptrend gate, testing whether Force Index's money-flow
signal (distinct from the volume-only VZO/CMF/MFI dials already tested)
generalizes once freed from a fixed-magnitude threshold.

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


def _efi_zscore_signal(df: pd.DataFrame, ema_span: int = 13, zscore_window: int = 100) -> pd.Series:
    """tanh(rolling z-score of EMA-smoothed Elder Force Index), bounded
    [-1, 1]. Normalizes for the fact that raw EFI = price_diff * volume has
    no fixed scale across symbols/time periods."""
    close = df["close"]
    volume = df["volume"]

    raw_efi = close.diff() * volume
    smoothed_efi = raw_efi.ewm(span=ema_span, adjust=False).mean()

    rolling_mean = smoothed_efi.rolling(zscore_window).mean()
    rolling_std = smoothed_efi.rolling(zscore_window).std().replace(0, np.nan)
    zscore = (smoothed_efi - rolling_mean) / rolling_std

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
    efi_ema_span: int = 13,
    efi_zscore_window: int = 100,
    base_exposure: float = 0.5,
    efi_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.28,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    efi_signal = _efi_zscore_signal(df, ema_span=efi_ema_span, zscore_window=efi_zscore_window)

    raw_exposure = base_exposure + efi_sensitivity * efi_signal
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    efi_ema_span: int = 13,
    efi_zscore_window: int = 100,
    base_exposure: float = 0.5,
    efi_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.28,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        efi_ema_span=efi_ema_span,
        efi_zscore_window=efi_zscore_window,
        base_exposure=base_exposure,
        efi_sensitivity=efi_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
