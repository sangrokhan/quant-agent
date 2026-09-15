"""Strategy: Ehlers Ultimate Channel base signal + inverse-volatility
position sizing overlay with no-trade rebalance buffer, full-universe MDD
rescue.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Direct fix for prior id 2026-09-16-133 (Ultimate Channel/Ultimate Bands
trend-following: ALL 4 symbols decisively failed max-drawdown at full
binary exposure, QQQ 0.350/SPY 0.379/BTC 0.579/ETH 0.632, roughly
1.4x-2.5x the 0.25 threshold, with marginal Sharpe on top). Unlike other
this-cron-trigger MDD-only rescues (Coral Trend, HalfTrend, CTI, TPR, which
only needed crypto rescued), this applies the repo's already-validated
inverse-volatility position-sizing overlay with a no-trade rebalance
buffer (construction unchanged from 2026-09-07-026, reused throughout this
cron trigger) to ALL FOUR symbols from the start, since equity also failed
MDD in the base version. No new external research this sub-iteration --
Ultimate Channel formula/source unchanged from 2026-09-16-133
(https://traders.com/Documentation/FEEDbk_docs/2024/05/TradersTips.html).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, vol_cap]).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _ultimate_smoother(src: pd.Series, period: int) -> pd.Series:
    period = max(int(period), 1)
    a1 = math.exp(-1.414 * math.pi / period)
    c2 = 2.0 * a1 * math.cos(1.414 * math.pi / period)
    c3 = -a1 * a1
    c1 = (1.0 + c2 - c3) / 4.0

    vals = src.ffill().fillna(0.0).to_numpy()
    n = len(vals)
    us = np.zeros(n)
    for i in range(n):
        if i < 4:
            us[i] = vals[i]
        else:
            us[i] = (
                (1.0 - c1) * vals[i]
                + (2.0 * c1 - c2) * vals[i - 1]
                - (c1 + c3) * vals[i - 2]
                + c2 * us[i - 1]
                + c3 * us[i - 2]
            )
    return pd.Series(us, index=src.index)


def _ultimate_channel_base_signal(
    high: pd.Series, low: pd.Series, close: pd.Series,
    length: int, str_length: int, num_strs: float,
) -> pd.Series:
    prev_close = close.shift(1)
    true_high = pd.concat([high, prev_close], axis=1).max(axis=1)
    true_low = pd.concat([low, prev_close], axis=1).min(axis=1)
    str_series = _ultimate_smoother(true_high - true_low, str_length)
    centerline = _ultimate_smoother(close, length)
    lower = centerline - num_strs * str_series

    in_uptrend = close > centerline
    pop_below = close < lower

    in_uptrend_arr = in_uptrend.fillna(False).to_numpy()
    pop_below_arr = pop_below.fillna(False).to_numpy()

    n = len(close)
    position = np.zeros(n)
    in_pos = False
    for i in range(n):
        if in_pos:
            if pop_below_arr[i]:
                in_pos = False
            else:
                position[i] = 1.0
        else:
            if in_uptrend_arr[i]:
                in_pos = True
                position[i] = 1.0

    return pd.Series(position, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 20,
    str_length: int = 20,
    num_strs: float = 1.0,
    vol_window: int = 20,
    target_vol: float = 0.15,
    vol_cap: float = 1.0,
    rebalance_buffer: float = 0.10,
) -> pd.Series:
    """Continuous {0..vol_cap} position-size series: Ultimate Channel base
    signal scaled by inverse-volatility targeting, with a no-trade
    rebalance buffer to cut turnover.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    base_signal = _ultimate_channel_base_signal(high, low, close, length, str_length, num_strs)

    log_ret = np.log(close / close.shift(1))
    realized_vol = log_ret.rolling(vol_window).std() * np.sqrt(252.0)
    raw_scale = (target_vol / realized_vol).clip(upper=vol_cap)
    raw_scale = raw_scale.fillna(0.0)
    desired_size = (base_signal * raw_scale).clip(lower=0.0, upper=vol_cap)

    held = np.zeros(len(desired_size))
    desired = desired_size.to_numpy()
    current = 0.0
    for i in range(len(desired)):
        if abs(desired[i] - current) > rebalance_buffer:
            current = desired[i]
        held[i] = current
    return pd.Series(held, index=close.index)


def generate_returns(
    price_df: pd.DataFrame,
    length: int = 20,
    str_length: int = 20,
    num_strs: float = 1.0,
    vol_window: int = 20,
    target_vol: float = 0.15,
    vol_cap: float = 1.0,
    rebalance_buffer: float = 0.10,
) -> pd.Series:
    """Daily strategy returns: prior-day held size * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    held = generate_signals(
        price_df,
        length=length,
        str_length=str_length,
        num_strs=num_strs,
        vol_window=vol_window,
        target_vol=target_vol,
        vol_cap=vol_cap,
        rebalance_buffer=rebalance_buffer,
    )
    daily_ret = close.pct_change().fillna(0.0)
    return held.shift(1).fillna(0.0) * daily_ret
