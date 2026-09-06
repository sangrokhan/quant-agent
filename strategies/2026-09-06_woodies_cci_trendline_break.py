"""Strategy: Woodie's CCI Trend-Line Break (TLB), long side.

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Per a RoboForex-sourced summary of Woodie's CCI "Trend Line Break" (TLB)
technique (surfaced via Google's AI overview for "Woodies CCI trend line
break strategy specific rules" -- source draws trend lines directly across
the CCI histogram's own peaks/troughs, not on the price chart):
  - Draw a trend line connecting a sequence of declining CCI peaks (a
    downward-sloping trend line across the CCI histogram itself).
  - Long entry: CCI breaks above that downward-sloping trend line.
  - Stronger setups: CCI exceeded +200 before the pullback that formed the
    trend line.
  - Higher-probability: the breakout happens close to the zero line.
  - Confirmation: the fast CCI "Turbo" line (6-period CCI) turns/crosses to
    confirm momentum backing the break.

This repo has no interactive trend-line-drawing tool, so we mechanize
"downward-sloping trend line across recent CCI peaks" as a rolling linear
regression fit to the standard (14-period) CCI series over a
`trendline_lookback`-bar window with a negative slope (a declining trend),
and detect a "break" as today's actual CCI exceeding the regression line's
extrapolated value by more than `break_margin` points -- capturing the same
"price/indicator breaks above its own recent declining trend" idea without
requiring literal peak-to-peak line drawing.

Signal logic:
- slow CCI: standard 14-period CCI.
- fast CCI ("Turbo"): 6-period CCI.
- Rolling OLS slope of slow CCI over `trendline_lookback` bars must be
  negative (declining trend line) as of yesterday.
- Extrapolate that regression line to today; entry requires today's actual
  slow CCI to exceed the extrapolated value by `break_margin` (the "break"),
  AND the extrapolated trend-line value at breakout be within
  `zero_proximity` of 0 (source's "breakout near zero is higher-probability"
  rule), AND fast CCI must be rising (fast_cci > fast_cci.shift(1),
  source's Turbo-line confirmation).
- Exit: slow CCI crosses back below zero, or a `max_hold_days` time-stop.

First trend-line-break (regression-slope-break) CCI strategy in this repo --
distinct from Woodie's CCI Zero-Line-Reject (2026-09-05-007, a bounce-off-
zero-without-crossing signal, not a diagonal trend-line break).

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _cci(df: pd.DataFrame, window: int) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    sma_tp = tp.rolling(window).mean()
    mean_dev = tp.rolling(window).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    cci = (tp - sma_tp) / (0.015 * mean_dev.replace(0, np.nan))
    return cci.fillna(0.0)


def _rolling_ols_slope_and_pred(series: pd.Series, window: int) -> tuple[pd.Series, pd.Series]:
    """Rolling OLS fit of `series` vs. bar-index over `window` bars, vectorized.
    Returns (slope, predicted_value_at_last_point_extrapolated_one_step)."""
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()
    x_centered = x - x_mean

    values = series.values.astype(float)
    n = len(values)
    slopes = np.full(n, np.nan)
    preds = np.full(n, np.nan)
    if n >= window:
        # sliding_window_view avoids an O(n) Python loop with per-step allocs
        windows = np.lib.stride_tricks.sliding_window_view(values, window)  # shape (n-window+1, window)
        y_mean = windows.mean(axis=1)
        slope = (windows * x_centered).sum(axis=1) / x_var
        intercept = y_mean - slope * x_mean
        pred_next = intercept + slope * window
        # windows[k] covers values[k:k+window]; this aligns to "as of" index k+window-1,
        # predicting one step beyond (index k+window) -- matches original loop's
        # slopes.iloc[i]/preds.iloc[i] for i in range(window, n) using values[i-window:i].
        slopes[window:] = slope[: n - window]
        preds[window:] = pred_next[: n - window]
    return pd.Series(slopes, index=series.index), pd.Series(preds, index=series.index)


def generate_signals(
    price_df: pd.DataFrame,
    slow_cci_window: int = 14,
    fast_cci_window: int = 6,
    trendline_lookback: int = 10,
    break_margin: float = 20.0,
    zero_proximity: float = 100.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    slow_cci = _cci(df, slow_cci_window)
    fast_cci = _cci(df, fast_cci_window)

    slope, trendline_pred = _rolling_ols_slope_and_pred(slow_cci, trendline_lookback)
    declining_trend = slope.shift(1) < 0

    breaks_above = (slow_cci - trendline_pred) > break_margin
    near_zero = trendline_pred.abs() < zero_proximity
    turbo_confirm = fast_cci > fast_cci.shift(1)

    entry = (
        declining_trend.fillna(False)
        & breaks_above.fillna(False)
        & near_zero.fillna(False)
        & turbo_confirm.fillna(False)
    )
    exit_signal = slow_cci < 0

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
