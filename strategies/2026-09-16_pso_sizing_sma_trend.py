"""Strategy: SMA(trend_window) directional gate with continuous Premier
Stochastic Oscillator (PSO, Lee Leibfarth) sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Premier Stochastic Oscillator (PSO), developed by Lee Leibfarth (TASC
August 2008), per Investopedia's exact-formula explainer visited this
iteration
(https://www.investopedia.com/articles/trading/10/premier_stochastic_oscillator_explained.asp)
and LazyBear's TradingView port (https://www.tradingview.com/v/xewuyTA1/,
also visited): "a rewired version of a short-period stochastic... provides
a quick response to changes in market direction." Exact construction:

    %K  = 8-period stochastic oscillator: 100*(C-L_n)/(H_n-L_n)
    S   = 5-period double-smoothed EMA of ((%K - 50) * 0.1)
    PSO = (exp(S) - 1) / (exp(S) + 1)

PSO is a tanh-like exponential normalization of a double-EMA-smoothed,
centered %K, producing a naturally bounded symmetric [-1,1] oscillator
(rather than the raw [0,100] StochRSI-style ratio already used by this
repo's StochCMO/StochMFI/StochRVI entries) -- first Premier Stochastic
Oscillator strategy in this repo, structurally distinct via its
double-EMA-smoothing-then-exponential-normalization step rather than a
raw min/max stochastic-of-oscillator ratio.

Source's own suggested rule: long trades on PSO crossing below -0.90 then
below -0.20 (an oversold-to-recovering sequence); short trades on the
mirror-image crossing above +0.90 then +0.20.

This iteration reframes PSO as a CONTINUOUS SIZING dial (already naturally
bounded [-1,1], used directly -- no additional rescaling needed) inside an
SMA(trend_window) uptrend gate with a deadband to cut turnover, following
this repo's established continuous-sizing-dial pattern.

Source: https://www.investopedia.com/articles/trading/10/premier_stochastic_oscillator_explained.asp
(exact formula) and https://www.tradingview.com/v/xewuyTA1/ (trading rules
context), both visited this iteration via browser_exec.

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


def _stochastic_k(df: pd.DataFrame, stoch_period: int) -> pd.Series:
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]
    lowest_low = low.rolling(stoch_period).min()
    highest_high = high.rolling(stoch_period).max()
    rng = (highest_high - lowest_low).replace(0.0, np.nan)
    pct_k = 100.0 * (close - lowest_low) / rng
    return pct_k


def _premier_stochastic(df: pd.DataFrame, stoch_period: int, smooth_period: int) -> pd.Series:
    pct_k = _stochastic_k(df, stoch_period)
    centered = (pct_k - 50.0) * 0.1
    s = centered.ewm(span=smooth_period, adjust=False).mean()
    s = s.ewm(span=smooth_period, adjust=False).mean()  # double-smoothed
    exp_s = np.exp(s.clip(-20, 20))  # clip to avoid overflow
    pso = (exp_s - 1.0) / (exp_s + 1.0)
    return pso


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
    stoch_period: int = 8,
    smooth_period: int = 5,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    PSO (already naturally bounded [-1,+1]) is used directly as a sizing
    dial (no additional z-score/tanh needed), gated by an SMA(trend_window)
    uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    dial = _premier_stochastic(df, stoch_period, smooth_period).fillna(0.0)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    stoch_period: int = 8,
    smooth_period: int = 5,
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
        stoch_period=stoch_period,
        smooth_period=smooth_period,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
