"""Strategy: SMA(trend_window) directional gate with continuous Blau's
Ergodic Candlestick Oscillator (ECO) sizing overlay + deadband,
leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-16-055, this cron trigger):
Blau's Ergodic Candlestick Oscillator (ECO), per Google AI-overview
(TradingView/Scribd/StockFetcher corroborating, visited this iteration via
browser_exec Google fallback): ECO = Smooth2(Close-Open) / Smooth2(High-Low),
where Smooth2 is a double-EMA smoothing (EMA(EMA(x, r), s), typically r=5,
s=26 per multiple corroborating sources). ECO divides double-smoothed
candlestick BODY (close-open, directional momentum) by double-smoothed
candlestick RANGE (high-low, total local volatility) -- naturally bounded
close to [-1,+1] since |close-open| <= high-low by construction. Distinct
from every prior Blau-family strategy in this repo (Ergodic Oscillator,
TSI, SMI -- all built from close-to-close price changes) since ECO is
built from each bar's own OPEN-vs-CLOSE candlestick body relative to its
own High-Low range, not from close-to-close returns. First
Ergodic-Candlestick-Oscillator-specific strategy in this repo.

Construction (continuous sizing dial): ECO is already naturally bounded
close to [-1,+1] (no z-score needed, same "direct rescale" pattern used
for other naturally-bounded oscillators in this repo), used directly as a
continuous exposure-sizing dial inside an SMA(trend_window) uptrend gate
with a deadband to cut turnover.

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


def _eco(open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series, r: int, s: int) -> pd.Series:
    """Blau's Ergodic Candlestick Oscillator: double-smoothed
    (close-open) / double-smoothed (high-low).
    """
    body = close - open_
    rng = high - low

    smooth_body = body.ewm(span=r, adjust=False).mean().ewm(span=s, adjust=False).mean()
    smooth_range = rng.ewm(span=r, adjust=False).mean().ewm(span=s, adjust=False).mean()

    eco = smooth_body / smooth_range.replace(0.0, np.nan)
    return eco.clip(lower=-1.0, upper=1.0)


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
    eco_r: int = 5,
    eco_s: int = 26,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    ECO (naturally bounded close to [-1,+1]) is used directly as a sizing
    dial, gated by an SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    open_, high, low, close = df["open"], df["high"], df["low"], df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    dial = _eco(open_, high, low, close, eco_r, eco_s).fillna(0.0)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    eco_r: int = 5,
    eco_s: int = 26,
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
        eco_r=eco_r,
        eco_s=eco_s,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
