"""Strategy: Single-asset adaptation of StashAway's Dynamic Factor Allocation
"momentum-based regime switching" trend/bull-bear signal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-XXX):
Per Tai/Leung/Jimenez, "Dynamic Factor Allocation via Momentum-Based Regime
Switching" (SSRN abstract_id=6224058, https://papers.ssrn.com/sol3/papers.
cfm?abstract_id=6224058, read via browser_exec -- the PDF itself is
paywalled/access-blocked, but the abstract plus a Google AI-overview
synthesis of the SSRN listing and the paperswithbacktest.com mirror
disclose the mechanism's two-hyperparameter shape): the paper's own
cross-sectional multi-factor regime signal is built from (1) a trend
estimate over a smoothing-length hyperparameter, then (2) a z-score
NORMALIZATION of that trend, itself SMOOTHED over a second hyperparameter
(the paper's own phrase: "the smoothing lengths for trend estimation and
z-score smoothing" are the model's only 2 tunables). Bull regime = smoothed
z-score > 0; Bear regime = smoothed z-score <= 0.

This repo's architecture is single-symbol (generate_returns_fn contract),
so the paper's cross-sectional multi-factor allocation layer is out of
scope (feasibility-blocked, same as all cross-sectional factor strategies
previously rejected in this repo) -- but the underlying REGIME-DETECTION
mechanism (trend estimate -> z-score normalize -> SMOOTH THE Z-SCORE
ITSELF, not just the trend) is a genuinely distinct construction from every
prior z-score/trend-gate strategy in this repo (which either z-score the
raw price/indicator directly, or smooth the trend but never smooth the
z-score a second time). Applied here as a single-asset long/flat regime
timer: long while the double-smoothed z-score is in "Bull" (>0), flat
during "Bear" (<=0).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 60,
    zscore_smooth_window: int = 20,
    zscore_lookback: int = 252,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    trend_window: smoothing length for the underlying trend estimate (SMA
        of price).
    zscore_lookback: rolling window used to compute the z-score's own
        mean/std baseline (not one of the paper's 2 headline hyperparams,
        but required to define "normalized" -- held fixed at a sensible
        default so trend_window/zscore_smooth_window remain the 2 tuned
        knobs, matching the paper's own 2-hyperparameter framing).
    zscore_smooth_window: smoothing length applied to the z-score series
        ITSELF (the paper's second hyperparameter) -- this double-smoothing
        (smooth the trend, THEN z-score it, THEN smooth the z-score) is
        what distinguishes this construction from this repo's other
        z-score-based regime gates.
    """
    df = _prep(price_df)
    close = df["close"]

    trend = close.rolling(trend_window).mean()
    trend_pct = trend.pct_change(trend_window)

    roll_mean = trend_pct.rolling(zscore_lookback).mean()
    roll_std = trend_pct.rolling(zscore_lookback).std()
    zscore = (trend_pct - roll_mean) / roll_std.replace(0, float("nan"))

    smoothed_zscore = zscore.rolling(zscore_smooth_window).mean()

    bull_regime = smoothed_zscore > 0
    signal = bull_regime.shift(1).fillna(False).astype(int)
    return signal


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 60,
    zscore_smooth_window: int = 20,
    zscore_lookback: int = 252,
) -> pd.Series:
    """Daily strategy returns, position-weighted, no transaction costs."""
    df = _prep(price_df)
    close = df["close"]
    positions = generate_signals(
        price_df,
        trend_window=trend_window,
        zscore_smooth_window=zscore_smooth_window,
        zscore_lookback=zscore_lookback,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = positions * daily_ret
    return strat_ret.fillna(0.0)
