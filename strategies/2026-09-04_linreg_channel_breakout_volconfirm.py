"""Strategy: Linear Regression Channel breakout with volume confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-141):
A rolling N-day OLS linear regression line through closing prices, plus
upper/lower bands at +/- k standard deviations of the residuals, forms a
statistically-defined trend channel. Per Google's AI-overview synthesis of
PyQuantLab/TradingView/FMZ explainers, a decisive close ABOVE the upper
regression band -- especially confirmed by above-average volume, guarding
against false breakouts -- signals continuation momentum strong enough to
break out of the recent statistical trend range; exit when price reverts to
touch the regression midline (take-profit) or a max_hold_days time-stop
backstop. This is distinct from the already-rejected pure regression-SLOPE
mean-reversion idea (id 2026-09-04-058, which faded on negative-slope
bounces) -- here the trade is momentum/breakout of the channel BAND itself,
not a slope-sign bet.

Signal logic
------------
- Rolling `channel_window`-day OLS regression of close vs time index ->
  fitted regression line `reg_line` and residual std `resid_std`.
- Upper band = reg_line + `band_k` * resid_std; lower band likewise.
- Volume confirmation: `volume > volume.rolling(vol_window).mean() *
  vol_mult` (avoid false low-volume breakouts).
- Entry (long): close crosses above upper band AND volume confirmation.
- Exit: close crosses back below reg_line (midline touch/take-profit), OR
  a max_hold_days time-stop backstop.
- Flat otherwise (long-only; no short leg per SAFETY.md scope).

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


def _rolling_regression_channel(close: pd.Series, channel_window: int):
    n = len(close)
    reg_line = pd.Series(index=close.index, dtype=float)
    resid_std = pd.Series(index=close.index, dtype=float)
    x = np.arange(channel_window)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    values = close.values
    for i in range(channel_window - 1, n):
        window = values[i - channel_window + 1 : i + 1]
        y_mean = window.mean()
        slope = ((x - x_mean) * (window - y_mean)).sum() / x_var
        intercept = y_mean - slope * x_mean
        fitted = intercept + slope * x
        resid = window - fitted
        reg_line.iloc[i] = fitted[-1]
        resid_std.iloc[i] = resid.std()

    return reg_line, resid_std


def generate_signals(
    price_df: pd.DataFrame,
    channel_window: int = 40,
    band_k: float = 2.0,
    vol_window: int = 20,
    vol_mult: float = 1.2,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    reg_line, resid_std = _rolling_regression_channel(close, channel_window)
    upper_band = reg_line + band_k * resid_std

    vol_confirm = volume > (volume.rolling(vol_window).mean() * vol_mult)

    cross_above_upper = (close > upper_band) & (close.shift(1) <= upper_band.shift(1))
    entry = cross_above_upper & vol_confirm.fillna(False)
    exit_signal = close < reg_line

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
