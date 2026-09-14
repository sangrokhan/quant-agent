"""Strategy: SMA(trend_window) directional gate with continuous
Gopalakrishnan Range Index (GAPO) inverse-volatility sizing overlay +
deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
GAPO (Gopalakrishnan Range Index, Jayanthi Gopalakrishnan 1994):
GAPO = ln(HighestHigh(n) - LowestLow(n)) / ln(n), a log-normalized N-period
high-low range volatility gauge. Formula confirmed in this repo's prior
entries (2026-09-07-010, 2026-09-08-050) and re-confirmed via StockSharp's
indicator documentation TOC this iteration
(https://doc.stocksharp.com/en/topics/api/indicators/list_of_indicators/gopalakrishnan_range_index).

This repo has 2 prior GAPO entries, both REJECTED binary
mean-reversion/breakout-anticipation triggers based on volatility-regime
percentile thresholds. Neither used GAPO as a continuous VOLATILITY-
CONDITIONING multiplier. This iteration instead uses GAPO as an INVERSE
scaling factor on exposure within the SMA(trend_window) uptrend gate:
high GAPO (expanding range/volatility) scales exposure DOWN toward
base_exposure (de-risking during choppy/volatile stretches), low GAPO
(contracting range) scales exposure UP toward leverage_cap (leaning in
during calm, orderly uptrends) -- the opposite conditioning direction from
RAVI (2026-09-14-134, which scales UP with trend-strength magnitude); GAPO
instead scales UP with volatility COMPRESSION, testing the alternate
"quiet uptrends are more reliable" hypothesis.

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


def _gapo(high: pd.Series, low: pd.Series, period: int = 14) -> pd.Series:
    """GAPO = ln(HighestHigh(period) - LowestLow(period)) / ln(period)."""
    hh = high.rolling(period).max()
    ll = low.rolling(period).min()
    rng = (hh - ll).clip(lower=1e-9)
    return np.log(rng) / np.log(period)


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
    gapo_period: int = 14,
    norm_window: int = 252,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    GAPO is min-max normalized against its own trailing `norm_window`
    distribution into [0, 1], then INVERTED (1 - normalized) so low
    volatility (compression) drives exposure UP toward leverage_cap.
    """
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    gapo = _gapo(high, low, gapo_period)

    roll_min = gapo.rolling(norm_window).min()
    roll_max = gapo.rolling(norm_window).max()
    gapo_norm = ((gapo - roll_min) / (roll_max - roll_min).replace(0, np.nan)).clip(0.0, 1.0)
    inv_gapo = 1.0 - gapo_norm

    raw_exposure = base_exposure + sensitivity * inv_gapo
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    gapo_period: int = 14,
    norm_window: int = 252,
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
        gapo_period=gapo_period,
        norm_window=norm_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
