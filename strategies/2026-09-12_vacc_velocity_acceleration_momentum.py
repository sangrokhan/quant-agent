"""Strategy: VAcc (Velocity + Acceleration momentum indicator) long entry.

Source: TASC (Technical Analysis of Stocks & Commodities) November 2023
Traders' Tips, Scott Cong "VAcc: A Momentum Indicator Based On Velocity And
Acceleration", via TradingView script index
https://www.tradingview.com/scripts/tasc/page-2/ (visited 2026-09-12, see
knowledge_base/visited_pages.jsonl).

Source's disclosed construction:
    For the current close C and each bar C(i) within a `lookback` window,
    velocity V(i) = (C - C(i)) / i  (i = 1..lookback, i.e. distance back).
    Average velocity = EMA-smoothed average of the V(i) series (smoothing
    span `velocity_smooth`).
    Acceleration Acc(i) = (V - V(i)) / i, where V is the current average
    velocity value; averaged (NOT further smoothed, per source) over the
    same lookback window to give "average acceleration".

Source's own disclosed trading conditions:
    Strong Upward: velocity rising AND acceleration rising above zero.
    Strong Downward: velocity falling AND acceleration falling below zero.

Operationalized here as a long-only strategy: enter long when velocity is
rising (today's smoothed velocity > yesterday's) AND acceleration crosses
above zero; exit (flat) on the mirror-image bearish condition (velocity
falling AND acceleration crosses below zero), or a max_hold_days time-stop.

Novelty vs prior KB entries: first velocity/acceleration "physics" indicator
in this repo -- source notes it behaves like MACD on long lookbacks and like
a less-saturated stochastic on short lookbacks, but the actual formula
(per-bar (C-C(i))/i averaging) is distinct from any MACD/stochastic
construction already tested.

Interface contract (see validation/grid_test.py, validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _vacc(close: pd.Series, lookback: int, velocity_smooth: int) -> tuple[pd.Series, pd.Series]:
    n = len(close)
    vals = close.values
    avg_velocity = np.full(n, np.nan)
    avg_acceleration = np.full(n, np.nan)

    raw_velocity = np.full(n, np.nan)
    for t in range(n):
        if t < lookback:
            continue
        vsum = 0.0
        for i in range(1, lookback + 1):
            vsum += (vals[t] - vals[t - i]) / i
        raw_velocity[t] = vsum / lookback

    raw_vel_series = pd.Series(raw_velocity, index=close.index)
    smoothed_velocity = raw_vel_series.ewm(span=velocity_smooth, adjust=False, min_periods=velocity_smooth).mean()
    avg_velocity = smoothed_velocity.values

    for t in range(n):
        if t < lookback or np.isnan(avg_velocity[t]):
            continue
        asum = 0.0
        count = 0
        for i in range(1, lookback + 1):
            if t - i < 0 or np.isnan(avg_velocity[t - i]):
                continue
            asum += (avg_velocity[t] - avg_velocity[t - i]) / i
            count += 1
        avg_acceleration[t] = asum / count if count > 0 else np.nan

    return pd.Series(avg_velocity, index=close.index), pd.Series(avg_acceleration, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 10,
    velocity_smooth: int = 5,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    velocity, acceleration = _vacc(close, lookback, velocity_smooth)

    velocity_rising = velocity.diff() > 0
    velocity_falling = velocity.diff() < 0
    accel_cross_up = (acceleration > 0) & (acceleration.shift(1) <= 0)
    accel_cross_down = (acceleration < 0) & (acceleration.shift(1) >= 0)

    entry = (velocity_rising & accel_cross_up).fillna(False)
    exit_signal = (velocity_falling & accel_cross_down).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
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
