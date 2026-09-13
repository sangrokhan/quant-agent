"""Strategy: SMA(trend_window) directional gate with continuous Schaff Trend
Cycle (STC) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-107):
Schaff Trend Cycle (Doug Schaff): double-smoothed stochastic-of-MACD
oscillator, natively bounded [0,100]. Formula confirmed via Google AI
overview (browser_exec fallback after `web_search` backend error --
DDGSException connection error to search.yahoo.com):
  1. MACD = EMA(fast, close) - EMA(slow, close)   [defaults fast=23, slow=50]
  2. %K1 = 100 * (MACD - LL(MACD, n)) / (HH(MACD, n) - LL(MACD, n))  [n=10]
  3. %D1 = EMA(smooth, %K1)   [smooth=3]
  4. %K2 = 100 * (%D1 - LL(%D1, n)) / (HH(%D1, n) - LL(%D1, n))
  5. STC = EMA(smooth, %K2), bounded [0, 100]

Repo has 6 prior STC entries, all binary crossover/oscillator-threshold
constructions (one accepted SPY-only at fast=23/slow=50/cycle=20/
centerline=50, one accepted QQQ-only with a zero-line-crossover + trend
gate). None reframed STC as a CONTINUOUS SIZING dial. Since STC is natively
bounded [0,100] like RSI/RMI/SMI (no z-score/tanh normalization needed --
just rescale to [-1,1] via (STC-50)/50), this iteration follows the
"natively-bounded oscillator -> continuous sizing dial within SMA trend
gate" pattern that worked well for VHF/PFE/RWI-diff/CHOP earlier this cron
trigger.

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


def _stochastic(series: pd.Series, n: int) -> pd.Series:
    lowest = series.rolling(n).min()
    highest = series.rolling(n).max()
    rng = (highest - lowest).replace(0, np.nan)
    return 100.0 * (series - lowest) / rng


def _stc_signal(
    df: pd.DataFrame,
    fast: int = 23,
    slow: int = 50,
    cycle: int = 10,
    smooth: int = 3,
) -> pd.Series:
    """Schaff Trend Cycle, bounded [0, 100]. Rescaled to [-1, 1] via
    (STC - 50) / 50 for use as a signed sizing dial."""
    close = df["close"]
    macd = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()

    k1 = _stochastic(macd, cycle)
    d1 = k1.ewm(span=smooth, adjust=False).mean()

    k2 = _stochastic(d1, cycle)
    stc = k2.ewm(span=smooth, adjust=False).mean()
    stc = stc.clip(lower=0.0, upper=100.0)

    return (stc - 50.0) / 50.0


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
    stc_fast: int = 23,
    stc_slow: int = 50,
    stc_cycle: int = 10,
    stc_smooth: int = 3,
    base_exposure: float = 0.5,
    stc_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    stc_signal = _stc_signal(df, fast=stc_fast, slow=stc_slow, cycle=stc_cycle, smooth=stc_smooth)

    raw_exposure = base_exposure + stc_sensitivity * stc_signal
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    stc_fast: int = 23,
    stc_slow: int = 50,
    stc_cycle: int = 10,
    stc_smooth: int = 3,
    base_exposure: float = 0.5,
    stc_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        stc_fast=stc_fast,
        stc_slow=stc_slow,
        stc_cycle=stc_cycle,
        stc_smooth=stc_smooth,
        base_exposure=base_exposure,
        stc_sensitivity=stc_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
