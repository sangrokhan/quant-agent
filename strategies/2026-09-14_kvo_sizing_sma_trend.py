"""Strategy: SMA(trend_window) directional gate with continuous Klinger
Volume Oscillator (KVO) sizing overlay + deadband, leverage-cap-aware for
crypto from the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Klinger Volume Oscillator (Stephen Klinger; formula per this repo's own
prior entries 2026-09-04-084/2026-09-11-122, sourced from LightningChart/
Investopedia -- no new browser fetch needed this iteration since the exact
disclosed formula is already in the knowledge base): Volume Force (VF)
combines signed volume (direction from the sum of High+Low+Close trend
vs its prior value) with the day's (High-Low) range as a volume-force
proxy; KVO = EMA(VF, 34) - EMA(VF, 55), further smoothed by a 13-period
EMA signal line. Repo has 2 prior KVO entries (2026-09-04-084 signal-line
crossover near-miss then fixed via min_hold_days in 2026-09-04-085
accepted SPY-only; 2026-09-11-122 gated crossover), all BINARY
crossover-based ENTRY constructions.

This iteration reframes KVO's raw (KVO - signal) spread as a CONTINUOUS
SIZING dial, normalized via a rolling z-score (same normalization
technique validated for Chaikin Oscillator, 2026-09-14-122, since KVO is
also volume*price-scale and not natively bounded), applying this cron
trigger's leverage-cap-aware crypto methodology (2026-09-14-124/125/126/
127) from the start.

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


def _klinger_volume_oscillator(
    df: pd.DataFrame, fast: int = 34, slow: int = 55, signal_span: int = 13
) -> pd.Series:
    """KVO = EMA(VF, fast) - EMA(VF, slow); return (KVO - signal_line).

    Volume Force (VF): trend direction (+1/-1) determined by the sign of
    the change in the typical-price sum (High+Low+Close) vs the prior
    bar's, scaled by volume and the day's (High-Low) range relative to a
    rolling normalization -- Klinger's own construction. Simplified per
    the standard public formula (Investopedia/LightningChart): dm =
    High - Low (daily range); cm = cumulative sum of dm while trend
    direction is unchanged, reset when trend flips; VF = Volume *
    abs(2*(dm/cm) - 1) * trend * 100.
    """
    high, low, close, volume = df["high"], df["low"], df["close"], df["volume"]
    hlc_sum = high + low + close
    trend = np.sign(hlc_sum.diff()).fillna(0.0)
    trend = trend.replace(0.0, np.nan).ffill().fillna(1.0)

    dm = high - low
    # cumulative range since the last trend flip
    trend_change = trend != trend.shift(1)
    group_id = trend_change.cumsum()
    cm = dm.groupby(group_id).cumsum()

    vf = volume * (2.0 * (dm / cm.replace(0, np.nan)) - 1.0).abs() * trend * 100.0
    vf = vf.fillna(0.0)

    kvo = vf.ewm(span=fast, adjust=False).mean() - vf.ewm(span=slow, adjust=False).mean()
    signal = kvo.ewm(span=signal_span, adjust=False).mean()
    return kvo - signal


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
    kvo_fast: int = 34,
    kvo_slow: int = 55,
    signal_span: int = 13,
    zscore_window: int = 90,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    kvo_spread = _klinger_volume_oscillator(df, fast=kvo_fast, slow=kvo_slow, signal_span=signal_span)
    kvo_mean = kvo_spread.rolling(zscore_window).mean()
    kvo_std = kvo_spread.rolling(zscore_window).std().replace(0, np.nan)
    kvo_zscore = ((kvo_spread - kvo_mean) / kvo_std).clip(lower=-2.5, upper=2.5)

    raw_exposure = base_exposure + sensitivity * (kvo_zscore / 2.5)
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    kvo_fast: int = 34,
    kvo_slow: int = 55,
    signal_span: int = 13,
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
        kvo_fast=kvo_fast,
        kvo_slow=kvo_slow,
        signal_span=signal_span,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
