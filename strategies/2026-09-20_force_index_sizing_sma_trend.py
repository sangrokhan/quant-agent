"""Strategy: SMA(trend_window) directional gate with continuous Elder Force
Index (EFI) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-20-027):
Elder's Force Index (EFI, Alexander Elder): raw 1-period EFI = (Close -
PriorClose) * Volume, smoothed with an EMA (per Google AI-overview
synthesis of StockCharts.com ChartSchool / LuxAlgo / Deepvue / Finlogix,
read via browser_exec since web_search's DDGS backend errored with a TLS
RequestError on every query attempted this iteration). This repo has 4
prior Force Index entries (2026-09-04-049 dual-EMA pullback trigger,
2026-09-05-048 divergence, 2026-09-09-086 2-period+STC confirmation,
2026-09-10-097 plain 13-period EMA zero-cross) -- ALL binary
crossover/divergence ENTRY triggers, ALL rejected (Sharpe/MDD near-misses
on the plain zero-cross variant specifically: QQQ Sharpe 0.910/MDD 0.309,
SPY Sharpe 0.852). None reframed EFI as a CONTINUOUS SIZING dial. This
iteration applies the same reframing pattern that has repeatedly rescued
other oscillator families in this repo (Vortex, Awesome Oscillator, KST,
TRIX, Qstick, Elder-Ray, Ulcer Index, TSV, BOP): within an SMA(trend_window)
uptrend gate, exposure scales continuously with a rolling z-scored,
tanh-squashed EFI(13) reading rather than triggering a discrete zero-line
threshold-cross entry -- directly testing whether the prior near-miss
rejections were a symptom of the binary all-or-nothing exposure construction
(full position flips on every zero-cross, maximizing whipsaw/transaction
cost exposure) rather than EFI itself lacking signal.

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


def _force_index(df: pd.DataFrame, ema_window: int = 13) -> pd.Series:
    """Raw 1-period EFI = (Close - PriorClose) * Volume, smoothed by an
    ema_window-period EMA (standard Elder trend-confirmation smoothing)."""
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)
    raw_efi = close.diff() * volume
    smoothed = raw_efi.ewm(span=ema_window, adjust=False).mean()
    return smoothed


def _zscore_tanh(series: pd.Series, window: int, sensitivity: float) -> pd.Series:
    """Rolling z-score of `series`, squashed via tanh into [-1, 1] so it can
    drive a bounded continuous exposure dial regardless of the raw EFI
    series' scale (which depends on price level and volume units)."""
    roll_mean = series.rolling(window).mean()
    roll_std = series.rolling(window).std().replace(0, np.nan)
    z = (series - roll_mean) / roll_std
    return np.tanh(sensitivity * z)


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
    efi_ema_window: int = 13,
    zscore_window: int = 100,
    base_exposure: float = 0.5,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    efi = _force_index(df, ema_window=efi_ema_window)
    dial = _zscore_tanh(efi, window=zscore_window, sensitivity=sensitivity)  # ~[-1, 1]

    raw_exposure = base_exposure + base_exposure * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    efi_ema_window: int = 13,
    zscore_window: int = 100,
    base_exposure: float = 0.5,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        efi_ema_window=efi_ema_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
