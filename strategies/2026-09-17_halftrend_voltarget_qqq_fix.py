"""Strategy: HalfTrend (everget) trend-state gate with an inverse-realized-
volatility exposure scalar, direct fix for 2026-09-17-083's QQQ near-miss.

Hypothesis (direct fix, no new external research needed -- source already
confirmed at 2026-09-17-083 this cron trigger):
2026-09-17-083 tested the HalfTrend (everget) binary long/flat trend-state
gate: accepted on SPY (amplitude=6) but a genuine near-miss on QQQ
(amplitude=2) -- Sharpe 1.42, TC-survival 1.36, walk-forward 1.0,
param-sensitivity 0.14 all comfortably pass, but MDD (0.255) marginally
exceeded the 0.25 cap by 0.5 percentage points. This iteration applies this
repo's standard rescue pattern (already validated for MAD/NVI/PVO/WaveTrend/
DEMA-spread/Coppock): scale exposure inversely to a rolling realized-
volatility estimate (target_vol / realized_vol, clipped to
[0, leverage_cap]) on top of the same binary HalfTrend trend-state gate,
so drawdowns during HalfTrend's rare high-vol whipsaw periods are damped
without changing the underlying entry/exit logic.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap])
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _halftrend_state(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    amplitude: int,
) -> pd.Series:
    """Port of everget's HalfTrend Pine v5 script (same as
    2026-09-17_halftrend_state_gate.py): returns the `trend` state series
    (0 = uptrend, 1 = downtrend)."""
    n = len(close)
    high_ma = high.rolling(amplitude, min_periods=amplitude).mean().to_numpy()
    low_ma = low.rolling(amplitude, min_periods=amplitude).mean().to_numpy()
    high_price = high.rolling(amplitude, min_periods=amplitude).max().to_numpy()
    low_price = low.rolling(amplitude, min_periods=amplitude).min().to_numpy()
    close_arr = close.to_numpy()
    prev_high = high.shift(1).to_numpy()
    prev_low = low.shift(1).to_numpy()

    trend = np.zeros(n, dtype=int)
    next_trend = np.zeros(n, dtype=int)
    max_low_price = np.full(n, np.nan)
    min_high_price = np.full(n, np.nan)

    start = amplitude
    if start >= n:
        return pd.Series(trend, index=close.index)

    max_low_price[start - 1] = prev_low[start] if not np.isnan(prev_low[start]) else low.iloc[start]
    min_high_price[start - 1] = prev_high[start] if not np.isnan(prev_high[start]) else high.iloc[start]

    for i in range(start, n):
        prev_next_trend = next_trend[i - 1]
        prev_max_low = max_low_price[i - 1]
        prev_min_high = min_high_price[i - 1]

        cur_trend = trend[i - 1]
        cur_next_trend = prev_next_trend
        cur_max_low = prev_max_low
        cur_min_high = prev_min_high

        if prev_next_trend == 1:
            cur_max_low = max(low_price[i], prev_max_low)
            if high_ma[i] < cur_max_low and close_arr[i] < prev_low[i]:
                cur_trend = 1
                cur_next_trend = 0
                cur_min_high = high_price[i]
        else:
            cur_min_high = min(high_price[i], prev_min_high)
            if low_ma[i] > cur_min_high and close_arr[i] > prev_high[i]:
                cur_trend = 0
                cur_next_trend = 1
                cur_max_low = low_price[i]

        trend[i] = cur_trend
        next_trend[i] = cur_next_trend
        max_low_price[i] = cur_max_low
        min_high_price[i] = cur_min_high

    return pd.Series(trend, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    amplitude: int = 2,
    vol_window: int = 20,
    target_vol: float = 0.12,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series.

    Binary HalfTrend trend-state gate (long only while trend==0) scaled by
    an inverse-realized-volatility exposure multiplier
    (target_vol / realized_vol, annualized, clipped to [0, leverage_cap]).
    """
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    trend = _halftrend_state(high, low, close, amplitude)
    gate = (trend == 0).astype(float)

    daily_ret = close.pct_change()
    realized_vol = daily_ret.rolling(vol_window, min_periods=vol_window // 2).std() * np.sqrt(252)
    vol_scalar = (target_vol / realized_vol.replace(0.0, np.nan)).clip(upper=leverage_cap)
    vol_scalar = vol_scalar.fillna(0.0)

    exposure = (gate * vol_scalar).clip(lower=0.0, upper=leverage_cap)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    amplitude: int = 2,
    vol_window: int = 20,
    target_vol: float = 0.12,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        amplitude=amplitude,
        vol_window=vol_window,
        target_vol=target_vol,
        leverage_cap=leverage_cap,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
