"""Strategy: Kaufman Adaptive Moving Average (KAMA) + volatility bands,
pullback-mode long entry.

Hypothesis (this iteration's research pipeline; web_search DDGS backend
returned "No results found" for multiple queries -> browser_exec Google
SERP fallback used): per PyQuantLab's "Adaptive MA Volatility Bands
(KAMA): Pullback vs Breakout" Medium article (confirmed via Google AI
Overview synthesis this iteration, browser_exec), KAMA (Perry Kaufman's
Efficiency-Ratio-adaptive moving average) combined with standard-deviation
volatility bands supports two distinct trading modes. This strategy
implements the PULLBACK mode (distinct from this repo's already-tested
plain KAMA crossover, id 2026-09-04-048, which used a dual-KAMA crossover
with no volatility bands at all):

- Regime filter: uptrend confirmed when close > KAMA AND KAMA's own slope
  is positive (source's own stated pullback-mode precondition).
- Entry: while in that uptrend regime, price dips below the LOWER
  adaptive band (KAMA - n_std * rolling_std) then recovers back above it
  -- "enter when the price dips and then crosses or rebounds back above
  the lower adaptive band" (source's exact rule).
- Exit: close falls back below the KAMA baseline (source's stated
  pullback-mode long-exit rule: "close the long position when the price
  falls back below the middle adaptive baseline (KAMA)").

KAMA itself (Efficiency Ratio-driven adaptive smoothing constant) uses the
standard Kaufman 1998 formula, matching this repo's prior KAMA
implementation (2026-09-04-048) for consistency.

Interface contract: both generate_signals and generate_returns accept all
tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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


def _kama(price: pd.Series, er_window: int, fast_period: int, slow_period: int) -> pd.Series:
    """Kaufman Adaptive Moving Average (Kaufman 1998 standard formula)."""
    change = (price - price.shift(er_window)).abs()
    volatility = price.diff().abs().rolling(er_window).sum()
    efficiency_ratio = (change / volatility).replace([np.inf, -np.inf], np.nan).fillna(0.0)

    fast_sc = 2.0 / (fast_period + 1.0)
    slow_sc = 2.0 / (slow_period + 1.0)
    smoothing_constant = (efficiency_ratio * (fast_sc - slow_sc) + slow_sc) ** 2

    p = price.to_numpy()
    sc = smoothing_constant.to_numpy()
    n = len(p)
    kama = np.zeros(n)
    kama[:er_window] = p[:er_window]
    for t in range(er_window, n):
        prev = kama[t - 1] if t > er_window else p[t - 1]
        kama[t] = prev + sc[t] * (p[t] - prev)
    return pd.Series(kama, index=price.index)


def generate_signals(
    price_df: pd.DataFrame,
    er_window: int = 10,
    fast_period: int = 2,
    slow_period: int = 30,
    band_window: int = 20,
    n_std: float = 2.0,
    slope_window: int = 5,
) -> pd.Series:
    """Return a 0/1 position series (pullback-mode long entries only)."""
    df = _prep(price_df)
    close = df["close"]

    kama = _kama(close, er_window, fast_period, slow_period)
    rolling_std = close.rolling(band_window).std()
    lower_band = kama - n_std * rolling_std

    kama_slope_positive = kama.diff(slope_window) > 0
    uptrend = (close > kama) & kama_slope_positive

    below_lower = close < lower_band
    recovered_above_lower = (close >= lower_band) & (close.shift(1) < lower_band.shift(1))

    entry = (uptrend & recovered_above_lower).fillna(False)
    exit_signal = (close < kama).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
