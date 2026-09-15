"""Strategy: SMA(trend_window) directional gate with continuous Stochastic
RVI (Stochastic applied to Dorsey's Relative Volatility Index) sizing
overlay + deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
"Stochastic RVI" (JohnBaron, TradingView, visited this iteration:
https://www.tradingview.com/scripts/rvi/ -- "Based on the Stochastic RSI but
uses RVI (Relative Volatility Index) as source. Another great tool for
finding market lows and entry points."): the classic StochRSI construction
(Stochastic Oscillator formula applied to a rolling window of RSI values,
instead of price) is generalized here to Donald Dorsey's Relative Volatility
Index (RVI, already tested in this repo as a plain midline-crossover
confirmation gate -- 2026-09-05-003, 2026-09-09-080) instead of RSI. Dorsey's
RVI is an RSI-shaped formula fed the standard deviation of close prices
split into up-move/down-move buckets (a directional-volatility measure,
range roughly [0,100] like RSI). Applying the Stochastic formula to RVI's
own recent high/low range (rather than to price or to RSI) produces a
natively [0,1]-bounded reading of "how extreme is the current directional-
volatility regime relative to its own recent range" -- distinct from every
prior RVI (Dorsey) or StochRSI/StochCMO construction already in this repo
(this cron trigger's prior StochCMO entry applied the same generalization
to CMO instead of RVI).

This iteration reframes Stochastic-RVI as a CONTINUOUS SIZING dial (already
naturally bounded [0,1], rescaled to [-1,1] via 2x-1, no z-score/tanh
needed) used as an exposure multiplier inside an SMA(trend_window) uptrend
gate with a deadband to cut turnover, following this repo's repeatedly
validated continuous-sizing-dial pattern for oscillator families.

Source: https://www.tradingview.com/scripts/rvi/ (visited this iteration,
browser_exec Google-SERP-then-TradingView-page path after web_search
returned an empty/garbage result for the discovery query, same pattern as
this trigger's prior StochCMO iteration).

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


def _dorsey_rvi(close: pd.Series, rvi_period: int, smoothing: int) -> pd.Series:
    """Donald Dorsey's Relative Volatility Index: an RSI-shaped formula fed
    the rolling standard deviation of close prices, split into up-move /
    down-move buckets by the sign of the day's price change.
    """
    std = close.rolling(rvi_period).std()
    diff = close.diff()
    up_std = std.where(diff > 0, 0.0)
    down_std = std.where(diff < 0, 0.0)
    up_smooth = up_std.ewm(span=smoothing, adjust=False).mean()
    down_smooth = down_std.ewm(span=smoothing, adjust=False).mean()
    denom = (up_smooth + down_smooth).replace(0.0, np.nan)
    rvi = 100.0 * up_smooth / denom
    return rvi


def _stoch_of_series(series: pd.Series, stoch_period: int) -> pd.Series:
    lo = series.rolling(stoch_period).min()
    hi = series.rolling(stoch_period).max()
    rng = (hi - lo).replace(0.0, np.nan)
    stoch = (series - lo) / rng
    return stoch.clip(lower=0.0, upper=1.0)


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
    rvi_period: int = 10,
    rvi_smoothing: int = 14,
    stoch_period: int = 14,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Stochastic RVI (already naturally bounded [0,1]) is rescaled to [-1,+1]
    via 2x-1 (no z-score/tanh needed since it's a native ratio) before use
    as a sizing dial, gated by an SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    rvi = _dorsey_rvi(close, rvi_period, rvi_smoothing)
    stoch_rvi = _stoch_of_series(rvi, stoch_period)
    dial = (2.0 * stoch_rvi.fillna(0.5)) - 1.0

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    rvi_period: int = 10,
    rvi_smoothing: int = 14,
    stoch_period: int = 14,
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
        rvi_period=rvi_period,
        rvi_smoothing=rvi_smoothing,
        stoch_period=stoch_period,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
