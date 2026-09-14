"""Strategy: SMA(trend_window) directional gate with continuous Accelerator
Oscillator (Bill Williams, AO minus its own SMA5 -- momentum acceleration)
sizing overlay + deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Accelerator Oscillator (AC, Bill Williams): AO = SMA(median_price,5) -
SMA(median_price,34) (median_price=(High+Low)/2); AC = AO - SMA(AO, 5) --
the deceleration/acceleration of the Awesome Oscillator's own momentum,
already zero-centered by construction. Formula confirmed via Google
AI-overview synthesis of TradingView/StocksTrader (browser_exec fallback
after web_search's DuckDuckGo backend returned "No results found" for the
prior query this iteration). This repo has 1 prior AC entry
(2026-09-06_accelerator_oscillator_minhold.py, a binary zero-line crossover
with min-hold gate). This iteration reframes AC as a CONTINUOUS SIZING
dial: rolling z-scored + tanh-squashed to [-1,1], used as a sizing
multiplier within an SMA(trend_window) uptrend gate, deadband to cut
turnover, leverage_cap for crypto -- distinct from the already-tested
continuous-sizing Awesome Oscillator itself (AO, this cron trigger,
2026-09-14-173), since AC is AO's second-derivative-like acceleration
signal rather than AO's own level. First Accelerator Oscillator
continuous-sizing variant in this repo.

Source: Google AI-overview synthesis (browser_exec fallback) of
TradingView/StocksTrader's Accelerator Oscillator formula pages.

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


def _accelerator_oscillator(
    high: pd.Series, low: pd.Series, fast_window: int, slow_window: int, ac_smooth_window: int
) -> pd.Series:
    median_price = (high + low) / 2.0
    ao = median_price.rolling(fast_window).mean() - median_price.rolling(slow_window).mean()
    ac = ao - ao.rolling(ac_smooth_window).mean()
    return ac


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
    fast_window: int = 5,
    slow_window: int = 34,
    ac_smooth_window: int = 5,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Accelerator Oscillator (already zero-centered by construction) is
    rolling z-scored over `zscore_window` bars and tanh-squashed to [-1,+1]
    before use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    trend_long = close > close.rolling(trend_window).mean()
    ac = _accelerator_oscillator(high, low, fast_window, slow_window, ac_smooth_window)

    roll_mean = ac.rolling(zscore_window).mean()
    roll_std = ac.rolling(zscore_window).std()
    zscore = (ac - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    fast_window: int = 5,
    slow_window: int = 34,
    ac_smooth_window: int = 5,
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
        fast_window=fast_window,
        slow_window=slow_window,
        ac_smooth_window=ac_smooth_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
