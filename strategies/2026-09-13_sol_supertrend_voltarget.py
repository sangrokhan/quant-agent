"""Strategy: SOL/XRP SuperTrend + inverse-volatility position-size overlay.

Direct follow-up to 2026-09-13-029 (plain SuperTrend on SOL/USDT: full-
sample Sharpe 1.480 genuinely CLEARS this repo's 1.0 threshold, but max
drawdown 62.9% massively exceeds the 25% cap). Per that entry's own
next-step suggestion: apply this repo's existing inverse-volatility-
targeting position-sizing overlay (same construction as accepted
2026-09-08-165 / 2026-09-03_btc_momentum_voltarget.py) directly to the
SuperTrend binary signal, to see if de-risking during high-realized-vol
stretches (which is when SOL's severe multi-year drawdowns concentrate)
can shrink MDD into an acceptable range while preserving the underlying
signal's genuine Sharpe edge.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's
id): SuperTrend's binary {0,1} position sizing lets the strategy ride full
SOL volatility whenever the trend signal is on, doing nothing to shrink
exposure during high-volatility stretches -- exactly when large drawdowns
compound (2026-09-03-003's finding for BTC momentum applies structurally
the same way here). Scaling position size by target_vol/realized_vol
(never levering above 1x, only ever scaling down) should cut the max
drawdown while the SuperTrend direction signal itself (already shown to
have positive Sharpe on SOL) continues doing the directional work.

Signal logic
------------
- Same SuperTrend direction signal as 2026-09-13_sol_supertrend.py
  (atr_period/multiplier, daily-resampled OHLC).
- Realized volatility: trailing vol_window-day annualized stdev of daily
  log returns (crypto convention: 365 periods/year, matching this repo's
  existing BTC vol-targeting strategy).
- Position size = min(1.0, target_annual_vol / realized_vol), applied
  multiplicatively to the SuperTrend direction (0 or 1).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a [0, 1] continuous position-size series aligned to
        price_df.index.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep_daily(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    daily = df.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    return daily


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def _supertrend_direction(df: pd.DataFrame, atr_period: int, multiplier: float) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    atr = _atr(df, atr_period)
    hl2 = (high + low) / 2
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr

    n = len(df)
    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    trend_up = pd.Series(True, index=df.index)

    for i in range(1, n):
        if close.iloc[i - 1] <= final_upper.iloc[i - 1]:
            final_upper.iloc[i] = min(basic_upper.iloc[i], final_upper.iloc[i - 1])
        else:
            final_upper.iloc[i] = basic_upper.iloc[i]

        if close.iloc[i - 1] >= final_lower.iloc[i - 1]:
            final_lower.iloc[i] = max(basic_lower.iloc[i], final_lower.iloc[i - 1])
        else:
            final_lower.iloc[i] = basic_lower.iloc[i]

        if trend_up.iloc[i - 1] and close.iloc[i] < final_lower.iloc[i]:
            trend_up.iloc[i] = False
        elif (not trend_up.iloc[i - 1]) and close.iloc[i] > final_upper.iloc[i]:
            trend_up.iloc[i] = True
        else:
            trend_up.iloc[i] = trend_up.iloc[i - 1]

    return trend_up


def generate_signals(
    price_df: pd.DataFrame,
    atr_period: int = 14,
    multiplier: float = 3.0,
    vol_window: int = 20,
    target_annual_vol: float = 0.12,
    periods_per_year: int = 365,
) -> pd.Series:
    """Return a [0,1] vol-targeted long/flat position-size series (daily bars)."""
    df = _prep_daily(price_df)
    close = df["close"]

    direction = _supertrend_direction(df, atr_period, multiplier).astype(float)

    log_ret = np.log(close / close.shift(1))
    realized_vol = log_ret.rolling(vol_window).std() * np.sqrt(periods_per_year)

    size = (target_annual_vol / realized_vol).clip(upper=1.0)
    size = size.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    position = (direction * size).clip(lower=0.0, upper=1.0)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs), daily bars."""
    df = _prep_daily(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
