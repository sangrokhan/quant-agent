"""Strategy: TPR-filtered SMA crossover + inverse-volatility position
sizing overlay with a no-trade rebalance buffer, for MDD control.

Hypothesis (knowledge_base id 2026-09-15-116):
Direct fix for this same cron trigger's prior entry 2026-09-16-115 (TPR
trend-persistence-filtered SMA crossover: QQQ/SPY both Sharpe near-misses
with walk-forward/TC/param-sensitivity all clean; BTC/USDT passed Sharpe
but decisively failed MDD 0.462; ETH/USDT near-missed Sharpe and
decisively failed MDD 0.541). That entry's own notes flagged that TPR is
a trend-strength filter, not a risk-control mechanism, and suggested a
vol-target overlay as the natural fix for the MDD failures. This
iteration adds this repo's already-validated inverse-volatility
position-sizing overlay WITH a no-trade rebalance buffer (per
2026-09-07-026's own established construction: scale =
clip(target_vol/realized_vol, upper=vol_cap), buffered so daily vol
noise doesn't inflate transaction-cost-survival trade counts) on top of
the unchanged TPR-filtered SMA crossover base signal. No new external
research this sub-iteration -- TPR mechanism source remains
https://financial-hacker.com/petra-on-programming-the-trend-persistence-indicator/;
vol-targeting-with-buffer construction reused unchanged from
2026-09-07-026.

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


def _tpr_filtered_crossover_base(
    close: pd.Series,
    fast_sma_period: int,
    slow_sma_period: int,
    tpr_sma_period: int,
    tpr_period: int,
    tpr_threshold: float,
    smooth_span: int,
) -> pd.Series:
    fast_sma = close.rolling(fast_sma_period).mean()
    slow_sma = close.rolling(slow_sma_period).mean()
    crossover_long = fast_sma > slow_sma

    sma_for_tpr = close.rolling(tpr_sma_period).mean()
    sma_slope = sma_for_tpr.diff()
    typical_slope_scale = sma_slope.abs().rolling(252, min_periods=60).median()
    slope_thr = 0.1 * typical_slope_scale

    is_up = (sma_slope > slope_thr).astype(float)
    is_down = (sma_slope < -slope_thr).astype(float)
    ctr_p = is_up.rolling(tpr_period).sum()
    ctr_m = is_down.rolling(tpr_period).sum()
    tpr_raw = 100.0 * (ctr_p - ctr_m).abs() / tpr_period
    tpr = tpr_raw.ewm(span=smooth_span, adjust=False).mean()

    base_signal = (crossover_long & (tpr > tpr_threshold)).fillna(False).astype(float)
    return base_signal


def generate_signals(
    price_df: pd.DataFrame,
    fast_sma_period: int = 10,
    slow_sma_period: int = 40,
    tpr_sma_period: int = 20,
    tpr_period: int = 15,
    tpr_threshold: float = 20.0,
    smooth_span: int = 5,
    vol_window: int = 20,
    target_vol: float = 0.15,
    vol_cap: float = 1.0,
    rebalance_buffer: float = 0.10,
) -> pd.Series:
    """Continuous {0..vol_cap} position-size series: base_signal (TPR-
    filtered SMA crossover) scaled by inverse-volatility targeting, with a
    no-trade rebalance buffer to cut turnover.
    """
    df = _prep(price_df)
    close = df["close"]

    base_signal = _tpr_filtered_crossover_base(
        close, fast_sma_period, slow_sma_period, tpr_sma_period, tpr_period, tpr_threshold, smooth_span
    )

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
    fast_sma_period: int = 10,
    slow_sma_period: int = 40,
    tpr_sma_period: int = 20,
    tpr_period: int = 15,
    tpr_threshold: float = 20.0,
    smooth_span: int = 5,
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
        fast_sma_period=fast_sma_period,
        slow_sma_period=slow_sma_period,
        tpr_sma_period=tpr_sma_period,
        tpr_period=tpr_period,
        tpr_threshold=tpr_threshold,
        smooth_span=smooth_span,
        vol_window=vol_window,
        target_vol=target_vol,
        vol_cap=vol_cap,
        rebalance_buffer=rebalance_buffer,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = held.shift(1).fillna(0.0) * daily_ret
    return strat_ret
