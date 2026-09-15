"""Strategy: CTI (Correlation Trend Indicator) regime gate + inverse-volatility
position sizing overlay with no-trade rebalance buffer, for crypto MDD rescue.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Direct fix for prior id 2026-09-16-119 (LuxAlgo Correlation Trend Indicator
regime gate, accepted QQQ/SPY but decisively rejected on BTC/USDT and
ETH/USDT due to MDD 0.570/0.569, more than 2x the 0.25 threshold -- Sharpe
passed comfortably on both crypto symbols, so this is a pure risk-control
gap, not a signal-quality problem). Adds this repo's already-validated
inverse-volatility position-sizing overlay with a no-trade rebalance buffer
(construction unchanged from 2026-09-07-026 / reused again at 2026-09-16-116)
on top of the unchanged CTI regime-gate base signal. No new external
research this sub-iteration -- CTI formula/source unchanged from
2026-09-16-119 (https://www.luxalgo.com/library/indicator/correlation-trend-indicator/).

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


def _rolling_pearson_vs_index(close: pd.Series, length: int) -> pd.Series:
    idx = np.arange(length, dtype=float)
    idx_mean = idx.mean()
    idx_centered = idx - idx_mean
    idx_ss = (idx_centered ** 2).sum()

    def _corr(window: np.ndarray) -> float:
        if np.isnan(window).any():
            return np.nan
        y = window - window.mean()
        denom = np.sqrt((y ** 2).sum() * idx_ss)
        if denom == 0:
            return 0.0
        return float((idx_centered * y).sum() / denom)

    return close.rolling(length).apply(_corr, raw=True)


def _cti_base_signal(close: pd.Series, length: int, trend_threshold: float) -> pd.Series:
    cti = _rolling_pearson_vs_index(close, length)
    return (cti > trend_threshold).fillna(False).astype(float)


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 20,
    trend_threshold: float = 0.5,
    vol_window: int = 20,
    target_vol: float = 0.15,
    vol_cap: float = 1.0,
    rebalance_buffer: float = 0.10,
) -> pd.Series:
    """Continuous {0..vol_cap} position-size series: CTI regime-gate base
    signal scaled by inverse-volatility targeting, with a no-trade
    rebalance buffer to cut turnover.
    """
    df = _prep(price_df)
    close = df["close"]

    base_signal = _cti_base_signal(close, length, trend_threshold)

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
    trend_threshold: float = 0.5,
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
        trend_threshold=trend_threshold,
        vol_window=vol_window,
        target_vol=target_vol,
        vol_cap=vol_cap,
        rebalance_buffer=rebalance_buffer,
    )
    daily_ret = close.pct_change().fillna(0.0)
    return held.shift(1).fillna(0.0) * daily_ret
