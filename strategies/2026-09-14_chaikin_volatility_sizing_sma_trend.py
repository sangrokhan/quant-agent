"""Strategy: SMA(trend_window) directional gate with continuous Chaikin
Volatility (percentage rate-of-change of EMA-smoothed high-low range)
sizing overlay + deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Chaikin Volatility (Marc Chaikin): CV = 100 * (EMA(High-Low, ema_window) -
EMA(High-Low, ema_window).shift(roc_window)) / EMA(High-Low,
ema_window).shift(roc_window) -- a percentage rate-of-change of an
EMA-smoothed high-low range, already zero-centered by construction. Formula
confirmed via repo's own prior entries (2026-09-04-133, 2026-09-09-079) and
Definedge Securities documentation. This repo has 2 prior Chaikin
Volatility entries, BOTH using it as a BINARY threshold/zero-line-cross
trigger for a separate entry signal (both rejected across all symbols).
Neither used CV's own continuous magnitude as a SIZING dial. This iteration
follows this cron trigger's repeatedly-validated continuous-sizing-dial
pattern: CV rolling z-scored + tanh-squashed to [-1,1], used as a sizing
multiplier within an SMA(trend_window) uptrend gate, deadband to cut
turnover, leverage_cap for crypto. First Chaikin Volatility
continuous-sizing variant in this repo.

Source: repo's own prior confirmed formula (2026-09-04-133,
2026-09-09-079, both citing trendspider.com/Definedge Securities); no new
external source needed this iteration -- pure technique variant on an
already-confirmed formula.

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


def _chaikin_volatility(
    high: pd.Series, low: pd.Series, ema_window: int, roc_window: int
) -> pd.Series:
    hl_range = high - low
    ema_range = hl_range.ewm(span=ema_window, adjust=False).mean()
    cv = (ema_range - ema_range.shift(roc_window)) / ema_range.shift(roc_window).replace(0.0, np.nan) * 100.0
    return cv


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
    ema_window: int = 10,
    roc_window: int = 10,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Chaikin Volatility (already zero-centered by construction) is rolling
    z-scored over `zscore_window` bars and tanh-squashed to [-1,+1] before
    use as a sizing dial (expansion scales exposure up, contraction scales
    exposure down, per source's own stated "rises from low = bullish"
    interpretation).
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    trend_long = close > close.rolling(trend_window).mean()
    cv = _chaikin_volatility(high, low, ema_window, roc_window)

    roll_mean = cv.rolling(zscore_window).mean()
    roll_std = cv.rolling(zscore_window).std()
    zscore = (cv - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ema_window: int = 10,
    roc_window: int = 10,
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
        ema_window=ema_window,
        roc_window=roc_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
