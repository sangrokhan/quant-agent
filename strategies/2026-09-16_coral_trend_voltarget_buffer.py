"""Strategy: Coral Trend Indicator (LazyBear) + inverse-volatility position
sizing overlay with no-trade rebalance buffer, for crypto MDD rescue.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Direct fix for prior id 2026-09-16-125 (Coral Trend color-flip trend-
following: QQQ/SPY accepted, BTC/USDT and ETH/USDT rejected -- Sharpe
passed comfortably on both crypto symbols (1.187/1.374) but MDD decisively
failed (0.583/0.485, roughly 2x the 0.25 threshold), a pure risk-control
gap not a signal-quality problem). Adds this repo's already-validated
inverse-volatility position-sizing overlay with a no-trade rebalance
buffer (construction unchanged from 2026-09-07-026, reused at
2026-09-16-116/120/123) on top of the unchanged Coral Trend base signal.
No new external research this sub-iteration -- Coral Trend formula/source
unchanged from 2026-09-16-125
(https://www.tradingview.com/script/AzQo1gRi-Coral-Trend-Indicator-LazyBear/).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, vol_cap]).
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


def _coral_trend(close: pd.Series, sm: int, cd: float) -> pd.Series:
    di = (sm - 1.0) / 2.0 + 1.0
    c1 = 2.0 / (di + 1.0)
    c2 = 1.0 - c1
    c3 = 3.0 * (cd * cd + cd * cd * cd)
    c4 = -3.0 * (2.0 * cd * cd + cd + cd * cd * cd)
    c5 = 3.0 * cd + 1.0 + cd * cd * cd + 3.0 * cd * cd

    src = close.to_numpy()
    n = len(src)
    i1 = np.zeros(n)
    i2 = np.zeros(n)
    i3 = np.zeros(n)
    i4 = np.zeros(n)
    i5 = np.zeros(n)
    i6 = np.zeros(n)

    for t in range(n):
        prev_i1 = i1[t - 1] if t > 0 else src[t]
        prev_i2 = i2[t - 1] if t > 0 else src[t]
        prev_i3 = i3[t - 1] if t > 0 else src[t]
        prev_i4 = i4[t - 1] if t > 0 else src[t]
        prev_i5 = i5[t - 1] if t > 0 else src[t]
        prev_i6 = i6[t - 1] if t > 0 else src[t]

        i1[t] = c1 * src[t] + c2 * prev_i1
        i2[t] = c1 * i1[t] + c2 * prev_i2
        i3[t] = c1 * i2[t] + c2 * prev_i3
        i4[t] = c1 * i3[t] + c2 * prev_i4
        i5[t] = c1 * i4[t] + c2 * prev_i5
        i6[t] = c1 * i5[t] + c2 * prev_i6

    cto = -(cd ** 3) * i6 + c3 * i5 + c4 * i4 + c5 * i3
    return pd.Series(cto, index=close.index)


def _coral_base_signal(close: pd.Series, sm: int, cd: float) -> pd.Series:
    cto = _coral_trend(close, sm, cd)
    rising = cto > cto.shift(1)
    falling = cto < cto.shift(1)

    n = len(close)
    color_state = np.zeros(n, dtype=int)
    rising_arr = rising.to_numpy()
    falling_arr = falling.to_numpy()
    for i in range(n):
        if rising_arr[i]:
            color_state[i] = 1
        elif falling_arr[i]:
            color_state[i] = -1
        else:
            color_state[i] = color_state[i - 1] if i > 0 else 0

    base = (color_state == 1).astype(float)
    return pd.Series(base, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    sm: int = 21,
    cd: float = 0.4,
    vol_window: int = 20,
    target_vol: float = 0.15,
    vol_cap: float = 1.0,
    rebalance_buffer: float = 0.10,
) -> pd.Series:
    """Continuous {0..vol_cap} position-size series: Coral Trend base
    signal scaled by inverse-volatility targeting, with a no-trade
    rebalance buffer to cut turnover.
    """
    df = _prep(price_df)
    close = df["close"]

    base_signal = _coral_base_signal(close, sm, cd)

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
    sm: int = 21,
    cd: float = 0.4,
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
        sm=sm,
        cd=cd,
        vol_window=vol_window,
        target_vol=target_vol,
        vol_cap=vol_cap,
        rebalance_buffer=rebalance_buffer,
    )
    daily_ret = close.pct_change().fillna(0.0)
    return held.shift(1).fillna(0.0) * daily_ret
