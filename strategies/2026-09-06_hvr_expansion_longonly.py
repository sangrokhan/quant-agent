"""Strategy: Historical Volatility Ratio (HVR) expansion long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-109),
sourced from https://doc.stocksharp.com/api-examples/2055_HVR.html
(StockSharp "Historical Volatility Ratio Strategy" example):
"Strategy based on the Historical Volatility Ratio (HVR). It compares
short-term volatility over 6 bars to long-term volatility over 100 bars
using log returns. When the ratio rises above the threshold, the system
goes long expecting volatility expansion. When it falls below the
threshold, the system goes short." Default params: ShortPeriod=6,
LongPeriod=100, RatioThreshold=1.0. HVR = StdDev(log_returns, ShortPeriod) /
StdDev(log_returns, LongPeriod).

This repo adapts the source's long/short-symmetric rule to long-only (per
repo convention and SAFETY.md — no short-selling infrastructure): long when
HVR > threshold (short-term realized volatility is expanding relative to
its long-term norm, i.e. the market just woke up from a calm period and a
directional move may be underway), flat otherwise. Distinct from every
prior volatility-regime strategy tested in this repo (Choppiness Index,
Bollinger Bandwidth squeeze, ATR-expansion breakout, VHF, Random Walk Index)
because HVR is specifically a RATIO of two horizon-different realized
volatilities of log returns, not a single-horizon range/ATR/efficiency
measure.

Signal logic
------------
- log_return[t] = ln(close[t] / close[t-1]).
- short_vol[t] = rolling std-dev of log_return over short_period bars.
- long_vol[t] = rolling std-dev of log_return over long_period bars.
- HVR[t] = short_vol[t] / long_vol[t].
- Long entry (position=1): HVR > ratio_threshold.
- Flat (position=0): HVR <= ratio_threshold.
- No look-ahead: position is lagged by 1 day in generate_returns as usual.
- A max_hold_days time-stop is NOT applied here since the source's own rule
  is itself a continuous regime-state gate (position tracks HVR state
  directly, not a discrete entry trigger needing an exit rule) -- position
  simply follows whichever side of the threshold HVR is on, each bar.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, position lagged by 1 day to avoid look-ahead bias)
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


def _hvr(close: pd.Series, short_period: int, long_period: int) -> pd.Series:
    log_return = np.log(close / close.shift(1))
    short_vol = log_return.rolling(short_period, min_periods=short_period).std()
    long_vol = log_return.rolling(long_period, min_periods=long_period).std()
    hvr = short_vol / long_vol.replace(0.0, np.nan)
    return hvr


def generate_signals(
    price_df: pd.DataFrame,
    short_period: int = 6,
    long_period: int = 100,
    ratio_threshold: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    hvr = _hvr(close, short_period, long_period)
    position = (hvr > ratio_threshold).fillna(False).astype(int)
    position.name = "position"
    return position


def generate_returns(
    price_df: pd.DataFrame,
    short_period: int = 6,
    long_period: int = 100,
    ratio_threshold: float = 1.0,
) -> pd.Series:
    """Return daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    position = generate_signals(
        df, short_period=short_period, long_period=long_period, ratio_threshold=ratio_threshold
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns.name = "strategy_returns"
    return strat_returns
