"""Strategy: HalfTrend (everget) + inverse-volatility position sizing overlay
with no-trade rebalance buffer, for crypto MDD rescue.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Direct fix for prior id 2026-09-16-122 (HalfTrend ATR-based trend-following,
QQQ/SPY accepted, BTC/USDT and ETH/USDT rejected -- BTC Sharpe passed but
MDD decisively failed 0.589; ETH near-missed Sharpe and decisively failed
MDD 0.643, both more than 2x the 0.25 threshold). Adds this repo's
already-validated inverse-volatility position-sizing overlay with a
no-trade rebalance buffer (construction unchanged from 2026-09-07-026,
reused at 2026-09-16-116/120) on top of the unchanged HalfTrend base signal.
No new external research this sub-iteration -- HalfTrend source unchanged
from 2026-09-16-122 (https://www.tradingview.com/script/U1SJ8ubc-HalfTrend/).

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


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    tr = _true_range(high, low, close)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def _halftrend_state(
    high: pd.Series, low: pd.Series, close: pd.Series, amplitude: int, channel_deviation: float
) -> pd.Series:
    n = len(close)
    _ = _atr(high, low, close, 100)  # atr2 unused directly in state logic beyond original source

    high_price = high.rolling(amplitude + 1, min_periods=1).max().to_numpy()
    low_price = low.rolling(amplitude + 1, min_periods=1).min().to_numpy()
    high_ma = high.rolling(amplitude, min_periods=1).mean().to_numpy()
    low_ma = low.rolling(amplitude, min_periods=1).mean().to_numpy()

    h = high.to_numpy()
    l = low.to_numpy()
    c = close.to_numpy()

    trend = np.zeros(n, dtype=int)
    next_trend = np.zeros(n, dtype=int)
    max_low_price = np.zeros(n)
    min_high_price = np.zeros(n)

    max_low_price[0] = l[0]
    min_high_price[0] = h[0]

    for i in range(n):
        prev_low = l[i - 1] if i > 0 else l[i]
        prev_high = h[i - 1] if i > 0 else h[i]
        if i == 0:
            continue

        trend[i] = trend[i - 1]
        next_trend[i] = next_trend[i - 1]
        max_low_price[i] = max_low_price[i - 1]
        min_high_price[i] = min_high_price[i - 1]

        if next_trend[i] == 1:
            max_low_price[i] = max(low_price[i], max_low_price[i])
            if high_ma[i] < max_low_price[i] and c[i] < prev_low:
                trend[i] = 1
                next_trend[i] = 0
                min_high_price[i] = high_price[i]
        else:
            min_high_price[i] = min(high_price[i], min_high_price[i])
            if low_ma[i] > min_high_price[i] and c[i] > prev_high:
                trend[i] = 0
                next_trend[i] = 1
                max_low_price[i] = low_price[i]

    return pd.Series(trend, index=close.index)


def _halftrend_base_signal(high, low, close, amplitude, channel_deviation) -> pd.Series:
    trend_state = _halftrend_state(high, low, close, amplitude, channel_deviation)
    return (trend_state == 0).astype(float)


def generate_signals(
    price_df: pd.DataFrame,
    amplitude: int = 4,
    channel_deviation: float = 1.5,
    vol_window: int = 20,
    target_vol: float = 0.15,
    vol_cap: float = 1.0,
    rebalance_buffer: float = 0.10,
) -> pd.Series:
    """Continuous {0..vol_cap} position-size series: HalfTrend base signal
    scaled by inverse-volatility targeting, with a no-trade rebalance
    buffer to cut turnover.
    """
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    base_signal = _halftrend_base_signal(high, low, close, amplitude, channel_deviation)

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
    amplitude: int = 4,
    channel_deviation: float = 1.5,
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
        amplitude=amplitude,
        channel_deviation=channel_deviation,
        vol_window=vol_window,
        target_vol=target_vol,
        vol_cap=vol_cap,
        rebalance_buffer=rebalance_buffer,
    )
    daily_ret = close.pct_change().fillna(0.0)
    return held.shift(1).fillna(0.0) * daily_ret
