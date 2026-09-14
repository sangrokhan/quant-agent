"""Strategy: SMA(trend_window) directional gate with continuous Know Sure
Thing (KST, Martin Pring) sizing overlay + deadband, leverage-cap-aware
for crypto from the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Know Sure Thing (Martin Pring; formula per this repo's own prior entries
2026-09-04-057/2026-09-08-157, sourced from QuantifiedStrategies.com/
Investopedia, no new fetch needed this iteration): a weighted sum of four
SMA-smoothed Rate-of-Change (ROC) legs at increasing lookback periods
(10/15/20/30 by Pring's classic convention), weighted x1/x2/x3/x4 --
designed to synthesize short, medium, and long-term momentum into one
composite oscillator.

This repo has 6+ prior KST entries (2026-09-04-057, 2026-09-06-100,
2026-09-07-017, 2026-09-08-132 [distinct multi-horizon vote, not KST
itself], 2026-09-08-157, 2026-09-08-047), all BINARY signal-line-
crossover or zero-line-crossover ENTRY constructions, all rejected. This
iteration reframes the raw KST value itself (not its signal-line spread,
distinct from the KVO variant tested earlier this cron trigger,
2026-09-14-128) as a CONTINUOUS SIZING dial via rolling z-score
normalization, applying this cron trigger's leverage-cap-aware crypto
methodology (2026-09-14-124/125/126/127/128) from the start.

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


def _roc(close: pd.Series, period: int) -> pd.Series:
    return (close / close.shift(period) - 1.0) * 100.0


def _kst(
    close: pd.Series,
    roc_periods: tuple[int, int, int, int] = (10, 15, 20, 30),
    sma_periods: tuple[int, int, int, int] = (10, 10, 10, 15),
    weights: tuple[int, int, int, int] = (1, 2, 3, 4),
) -> pd.Series:
    """KST = sum(w_i * SMA(ROC(close, roc_period_i), sma_period_i)) for
    i=1..4, Pring's classic construction: ROC periods 10/15/20/30, each
    SMA-smoothed (10/10/10/15), weighted 1/2/3/4.
    """
    legs = []
    for roc_p, sma_p, w in zip(roc_periods, sma_periods, weights):
        leg = _roc(close, roc_p).rolling(sma_p).mean() * w
        legs.append(leg)
    return sum(legs)


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
    kst = _kst(close)
    kst_mean = kst.rolling(zscore_window).mean()
    kst_std = kst.rolling(zscore_window).std().replace(0, np.nan)
    kst_zscore = ((kst - kst_mean) / kst_std).clip(lower=-2.5, upper=2.5)

    raw_exposure = base_exposure + sensitivity * (kst_zscore / 2.5)
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
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
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
