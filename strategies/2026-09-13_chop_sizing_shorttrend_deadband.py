"""Strategy: SMA(short trend_window) directional gate with continuous
Choppiness Index (CHOP) INVERSE sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-13-094):
Choppiness Index (Bill Dreiss), bounded [0, 100]: CHOP =
100*log10(sum(TR,n)/(max(High,n)-min(Low,n)))/log10(n) -- low readings
(<38) indicate a trending regime, high readings (>62) indicate a choppy/
ranging regime (this repo's own well-established formula, 8+ prior entries,
all used as a binary threshold REGIME GATE restricting some other entry
signal to CHOP<threshold periods, e.g. 2026-09-04-059/2026-09-09-008/
2026-09-08-048/2026-09-09-075). This iteration instead uses CHOP as a
CONTINUOUS SIZING dial (the construction validated 10x already this cron
trigger for other bounded indicators, most recently ADX-092/DMI-diff-093):
exposure = clip(base_exposure + chop_sensitivity*((chop_reference-chop)/
chop_reference), 0, leverage_cap) within the SMA(trend_window) uptrend gate
-- exposure rises as CHOP falls below its reference level (increasingly
trending/efficient market, lean in harder), falls as CHOP rises above it
(increasingly choppy, de-risk even while the SMA gate stays nominally
long). Conceptually similar in spirit to the ADX/DMI-diff sizing dials
(both are trend-strength/regime-quality measures rather than directional
oscillators) but CHOP uses a fundamentally different log-ratio-of-ranges
construction (Dreiss's own formula, unrelated to Wilder's smoothed
directional movement that underlies ADX/DMI), making this a structurally
distinct sizing signal.

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


def _choppiness(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """Choppiness Index, bounded [0, 100]. Low = trending, high = choppy."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prior_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - prior_close).abs(),
            (low - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    tr_sum = tr.rolling(window).sum()
    range_high = high.rolling(window).max()
    range_low = low.rolling(window).min()
    range_span = (range_high - range_low).replace(0, np.nan)

    chop = 100.0 * np.log10(tr_sum / range_span) / np.log10(window)
    return chop.clip(lower=0.0, upper=100.0)


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
    chop_window: int = 14,
    chop_reference: float = 50.0,
    base_exposure: float = 0.8,
    chop_sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    chop = _choppiness(df, window=chop_window)

    raw_exposure = base_exposure + chop_sensitivity * ((chop_reference - chop) / chop_reference)
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    chop_window: int = 14,
    chop_reference: float = 50.0,
    base_exposure: float = 0.8,
    chop_sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        chop_window=chop_window,
        chop_reference=chop_reference,
        base_exposure=base_exposure,
        chop_sensitivity=chop_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
