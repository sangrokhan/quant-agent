"""Strategy: Standard Deviation Channel (linear regression) pullback-to-line continuation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-100):
Per https://www.lumleytrading.com/standard-deviation-channels/'s "Trend
Continuation at the Regression Line" strategy: "In a steeply ascending
channel, the regression line and the lower +/-1 sigma band often act as
dynamic support. When price pulls back to the regression line in a strong
uptrend, this is often a high-probability long entry. The steeper the
channel slope, the more conviction the underlying trend has."

This is distinct from three prior Standard-Deviation/Linear-Regression
strategies already in this repo: 2026-09-04-046 (mean-reversion to a plain
SMA20 midline, not a regression line, and gated by an unrelated SMA200
trend filter), 2026-09-04-141 (trades the channel BAND BREAKOUT direction,
not a pullback), and 2026-09-06-126 (Standard Error Bands with a
band-width-narrowing filter, an entirely different trigger). This strategy
is the first to trade a PULLBACK TO the regression line itself as a
trend-continuation entry, gated by the regression slope's steepness.

Signal logic
------------
- Rolling N-day OLS linear regression of close vs. time index ->
  regression line value at the current bar, and slope (per-bar price
  change implied by the fit).
- Steep uptrend: slope > 0 AND slope (as a fraction of price) >=
  min_slope_pct (the source's "steeper = more conviction" criterion).
- Pullback: close within pullback_tolerance (fractional) of the regression
  line value (source: "price pulls back to the regression line").
- Entry (long): pullback condition true while in a steep uptrend.
- Exit: close crosses back below the regression line by more than
  pullback_tolerance (failed support), the slope condition breaks, or a
  max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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


def _rolling_regression(close: pd.Series, window: int):
    """Return (regression_value_at_last_point, slope_per_bar) rolling series."""
    n = len(close)
    reg_val = pd.Series(np.nan, index=close.index)
    slope = pd.Series(np.nan, index=close.index)
    x = np.arange(window)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()
    vals = close.to_numpy()
    for i in range(window - 1, n):
        y = vals[i - window + 1 : i + 1]
        y_mean = y.mean()
        b = ((x - x_mean) * (y - y_mean)).sum() / x_var
        a = y_mean - b * x_mean
        fitted_last = a + b * (window - 1)
        reg_val.iloc[i] = fitted_last
        slope.iloc[i] = b
    return reg_val, slope


def generate_signals(
    price_df: pd.DataFrame,
    reg_window: int = 20,
    min_slope_pct: float = 0.002,
    pullback_tolerance: float = 0.01,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    reg_val, slope = _rolling_regression(close, reg_window)
    slope_pct = slope / close.replace(0, np.nan)

    steep_uptrend = (slope > 0) & (slope_pct >= min_slope_pct)
    near_line = (close - reg_val).abs() <= (pullback_tolerance * reg_val.abs())
    below_line = close < reg_val * (1 - pullback_tolerance)

    entry = near_line & steep_uptrend.fillna(False)
    exit_fail = below_line
    exit_trend_break = ~steep_uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_fail.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
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
