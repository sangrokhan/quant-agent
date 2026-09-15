"""Strategy: SMA(trend_window) directional gate with continuous T3
(Tillson, sextuple-cascaded EMA) distance-from-price sizing overlay +
deadband, leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-16-051, this cron trigger):
Tillson's T3 moving average (per TradingPedia/HaasOnline, already
documented in this repo from prior ids 2026-09-04-131/2026-09-05-090/
2026-09-06-108 -- formula not re-fetched this sub-iteration, only the exact
coefficient formula confirmed via a fresh Google query this iteration since
this repo's prior T3 entries didn't record the full e1..e6/c1..c4
derivation): e1=EMA(close,period), e2=EMA(e1,period), ..., e6=EMA(e5,
period); with volume factor b (default 0.7): c1=-b^3, c2=3b^2+3b^3,
c3=-6b^2-3b-3b^3, c4=1+3b+b^3+3b^2; T3 = c1*e6 + c2*e5 + c3*e4 + c4*e3.
This repo has 3 prior T3/Coral entries, all using T3 as a DISCRETE trigger
(slope-flip near-miss id 2026-09-04-131, price-crosses-T3 accepted-SPY-only
id 2026-09-05-090, dual-T3-crossover rejected id 2026-09-06-108) -- none as
a continuous sizing dial. This iteration reinterprets T3 per this repo's
established distance-from-MA continuous-sizing-dial pattern (cf. PMO, RVI,
DPO): T3's smoothness (near-zero lag, minimal overshoot) may make a
close-minus-T3 distance dial less noisy/lower-turnover than the discrete
crossover variants already tried.

Construction (continuous sizing dial): percent-distance of close from its
own T3(t3_window, b), rolling z-scored and tanh-squashed into [-1,+1], used
as a continuous exposure-sizing dial inside an SMA(trend_window) uptrend
gate with a deadband to cut turnover.

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


def _t3(close: pd.Series, period: int, b: float) -> pd.Series:
    """Tillson's T3 moving average: sextuple-cascaded EMA with a
    polynomial recombination controlled by volume factor `b`.
    """
    e1 = close.ewm(span=period, adjust=False).mean()
    e2 = e1.ewm(span=period, adjust=False).mean()
    e3 = e2.ewm(span=period, adjust=False).mean()
    e4 = e3.ewm(span=period, adjust=False).mean()
    e5 = e4.ewm(span=period, adjust=False).mean()
    e6 = e5.ewm(span=period, adjust=False).mean()

    c1 = -(b ** 3)
    c2 = 3.0 * b ** 2 + 3.0 * b ** 3
    c3 = -6.0 * b ** 2 - 3.0 * b - 3.0 * b ** 3
    c4 = 1.0 + 3.0 * b + b ** 3 + 3.0 * b ** 2

    t3 = c1 * e6 + c2 * e5 + c3 * e4 + c4 * e3
    return t3


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
    t3_window: int = 10,
    t3_b: float = 0.7,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Percent-distance of close from its own T3(t3_window, t3_b) is rolling
    z-scored over `zscore_window` and tanh-squashed to [-1,+1] before use
    as a sizing dial, gated by an SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    t3 = _t3(close, t3_window, t3_b)
    pct_dist = (close - t3) / t3.replace(0.0, np.nan)

    roll_mean = pct_dist.rolling(zscore_window).mean()
    roll_std = pct_dist.rolling(zscore_window).std()
    zscore = (pct_dist - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    t3_window: int = 10,
    t3_b: float = 0.7,
    zscore_window: int = 100,
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
        t3_window=t3_window,
        t3_b=t3_b,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
