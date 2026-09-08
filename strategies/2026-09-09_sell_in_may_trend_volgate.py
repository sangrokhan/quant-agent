"""Strategy: Sell in May / Halloween Effect gated by trend + low-volatility regime.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Direct fix for near-miss 2026-09-09-019 (plain Sell in May / Halloween
effect: 100% long Nov-Apr, flat May-Oct). That strategy's own grid found
the edge concentrated almost entirely in the low-volatility tercile
(12/24 low-vol grid cells passed vs 1/24 mid-vol, 0/24 high-vol) yet its
full-sample validation failed on MDD (0.311/0.341, both breaching the 25%
threshold) because being long the entire winter window with no additional
filter captures full drawdown exposure during any winter-window
volatility spike (e.g. Feb/Mar 2020, 2022 bear market months that happen
to fall inside Nov-Apr). This iteration's fix: keep the same calendar
window, but ALSO require (a) close > SMA(trend_window) (source's own
implicit "equities in an uptrend" framing) and (b) trailing realized
volatility below its own rolling percentile threshold (the exact
low-vol-regime condition the original grid empirically found necessary),
gating out winter-window periods that are actually in a downtrend or
elevated-vol regime.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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


def generate_signals(
    price_df: pd.DataFrame,
    long_start_month: int = 10,
    long_end_month: int = 3,
    trend_window: int = 100,
    vol_window: int = 20,
    vol_percentile_window: int = 252,
    vol_percentile_threshold: float = 0.6,
) -> pd.Series:
    """Return a {0,1} long/flat position series: long only when (a) within
    the Nov-Apr-style seasonal window, (b) close > SMA(trend_window), and
    (c) trailing realized volatility is below its own rolling
    `vol_percentile_threshold` percentile (a low/mid-vol regime gate)."""
    df = _prep(price_df)
    close = df["close"]
    months = df.index.month

    if long_start_month <= long_end_month:
        in_window = (months >= long_start_month) & (months <= long_end_month)
    else:
        in_window = (months >= long_start_month) | (months <= long_end_month)
    in_window = pd.Series(in_window, index=df.index)

    sma = close.rolling(trend_window, min_periods=trend_window).mean()
    uptrend = close > sma

    daily_ret = close.pct_change()
    realized_vol = daily_ret.rolling(vol_window, min_periods=vol_window).std()
    vol_rank = realized_vol.rolling(vol_percentile_window, min_periods=vol_percentile_window).rank(pct=True)
    low_vol = vol_rank <= vol_percentile_threshold

    position = (in_window & uptrend.fillna(False) & low_vol.fillna(False)).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
