"""Strategy: TSI centerline+signal crossover with a long-term trend gate,
direct fix for 2026-09-17-081's SPY near-miss.

Hypothesis (direct fix, no new external research needed -- TSI
formula/rules already confirmed at 2026-09-17-081 this cron trigger):
2026-09-17-081 tested TSI (William Blau) centerline+signal-line crossover:
accepted on QQQ but SPY was a near-miss (Sharpe 0.864 at grid-best config,
best hand-tuned local sweep over 180 combos still only 0.980, both <1.0).
This iteration adds a simple SMA(trend_window) long-term trend gate on top
of the same TSI entry/exit condition (long only when TSI>0 AND
TSI>signal-line AND close>SMA(trend_window)) to filter out the whipsaw
trades during range-bound/bearish regimes that likely dragged down SPY's
full-period Sharpe, without changing the core TSI construction.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _tsi(close: pd.Series, long_period: int, short_period: int) -> pd.Series:
    price_change = close.diff()
    abs_change = price_change.abs()

    smoothed_change = price_change.ewm(span=long_period, adjust=False).mean()
    double_smoothed_change = smoothed_change.ewm(span=short_period, adjust=False).mean()

    smoothed_abs = abs_change.ewm(span=long_period, adjust=False).mean()
    double_smoothed_abs = smoothed_abs.ewm(span=short_period, adjust=False).mean()

    tsi = 100 * double_smoothed_change / double_smoothed_abs.replace(0.0, pd.NA)
    return tsi.astype(float)


def generate_signals(
    price_df: pd.DataFrame,
    long_period: int = 25,
    short_period: int = 13,
    signal_period: int = 7,
    trend_window: int = 200,
) -> pd.Series:
    """Return a 0/1 position series.

    Long when TSI > 0 AND TSI > its own signal line (2026-09-17-081's
    original condition) AND close > SMA(trend_window) (new trend gate,
    this fix's addition).
    """
    df = _prep(price_df)
    close = df["close"]

    tsi = _tsi(close, long_period, short_period)
    signal_line = tsi.ewm(span=signal_period, adjust=False).mean()
    trend_sma = close.rolling(trend_window, min_periods=trend_window // 2).mean()

    position = ((tsi > 0) & (tsi > signal_line) & (close > trend_sma)).astype(float)
    position = position.fillna(0.0)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    long_period: int = 25,
    short_period: int = 13,
    signal_period: int = 7,
    trend_window: int = 200,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        long_period=long_period,
        short_period=short_period,
        signal_period=signal_period,
        trend_window=trend_window,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
