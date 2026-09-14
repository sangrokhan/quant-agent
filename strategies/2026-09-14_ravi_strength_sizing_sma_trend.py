"""Strategy: SMA(trend_window) directional gate with continuous Range
Action Verification Index (RAVI, Tushar Chande) trend-strength sizing
overlay + deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
RAVI (Tushar Chande, "Beyond Technical Analysis"): RAVI = 100 * abs(fastMA
- slowMA) / slowMA (default fast SMA(7), slow SMA(65)) -- an always-
non-negative percentage measure of how far a short moving average has
diverged from a long one, used as a trend-strength/ranging-market gauge
(low RAVI = ranging, high RAVI = strongly trending). Confirmed via the
open-source Pine Script on
https://www.tradingview.com/script/pZkdfat6-Range-Action-Verification-Index-RAVI/
(visited this iteration, browser_exec fallback after web_search DDGS
backend returned no results/TLS errors for several RAVI queries).

First RAVI strategy in this repo (0 prior entries). Since RAVI itself
carries no directional sign (it's an absolute-value magnitude), this
iteration uses it as a CONVICTION multiplier rather than a bipolar sizing
dial like most other indicators tested this cron trigger: within the
existing SMA(trend_window) uptrend gate, exposure scales UP with RAVI
magnitude (min-max normalized against a rolling reference) -- the stronger
the fast/slow MA divergence, the more confidently we lean into the
already-confirmed uptrend; exposure scales DOWN toward base_exposure when
RAVI is low (a ranging/directionless market, per Chande's own
interpretation), even while technically above the trend gate.

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


def _ravi(close: pd.Series, fast_period: int = 7, slow_period: int = 65) -> pd.Series:
    """RAVI = 100 * abs(fastSMA - slowSMA) / slowSMA, always >= 0."""
    fast_ma = close.rolling(fast_period).mean()
    slow_ma = close.rolling(slow_period).mean()
    return 100.0 * (fast_ma - slow_ma).abs() / slow_ma.replace(0, np.nan)


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
    ravi_fast: int = 7,
    ravi_slow: int = 65,
    norm_window: int = 252,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    RAVI is min-max normalized against its own trailing `norm_window`
    distribution (RAVI has no fixed natural bound, unlike prior sizing-dial
    indicators tested this cron trigger) into [0, 1], then used to scale
    exposure UP from `base_exposure` toward `leverage_cap` as trend
    strength increases.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    ravi = _ravi(close, ravi_fast, ravi_slow)

    roll_min = ravi.rolling(norm_window).min()
    roll_max = ravi.rolling(norm_window).max()
    ravi_norm = ((ravi - roll_min) / (roll_max - roll_min).replace(0, np.nan)).clip(0.0, 1.0)

    raw_exposure = base_exposure + sensitivity * ravi_norm
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ravi_fast: int = 7,
    ravi_slow: int = 65,
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
        ravi_fast=ravi_fast,
        ravi_slow=ravi_slow,
        norm_window=norm_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
