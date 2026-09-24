"""Strategy: Trend Quality Indicator (TQI) zero-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://www.tradingview.com/script/wWgA0nGW-Trend-Quality-Indicator-TQI-TR/
(tiagorocha1989, open-source Pine script; read via browser_exec after
web_search's DDGS backend returned unrelated/garbage results this
iteration), whose own "How It Works" section discloses the full
calculation:

    "Linear Regression Slope – Slope of a linear regression line fitted to
    close over Length_TQI periods.
    Normalised Slope – slope / ATR(ATR_Length_TQI). This makes the slope
    comparable across different price and volatility scales.
    R-Squared (R2) – Computed as sum((regression_value - mean)^2) /
    sum((close - mean)^2). It represents the proportion of price variance
    explained by the linear trend.
    Raw TQI – normalised_slope * R2. Multiplying by R2 penalises trends
    that are not linear (i.e., choppy or curved moves).
    Smoothed TQI – Simple moving average of raw TQI over Smooth_TQI
    periods. This is the final signal line."

    Entry signals: "LONG – Smoothed TQI crosses above the zero line ...
    SHORT – Smoothed TQI crosses below the zero line."

First Trend Quality Index / TQI entry in this repo (0 prior index hits).
Structurally distinct from every prior indicator tested: it is the first
strategy in this repo that multiplies a normalized linear-regression slope
by the regression's own R^2 goodness-of-fit, explicitly penalizing
statistically noisy/curved trends rather than just gating on a separate
trend-strength filter (ADX, Hurst, etc. as used by ~20 other entries) --
the "quality" weighting is baked directly into the single oscillator value
used for the entry/exit decision itself, not a secondary AND-gate.

Signal logic (long-only translation of the source's LONG/SHORT rule)
----------------------------------------------------------------------
- Over a rolling `length` window, fit an OLS linear regression of close
  vs. bar index; take its slope and R^2 (fraction of price variance
  explained by the linear fit).
- normalised_slope = slope / ATR(atr_length) (per source's own ATR
  normalization for cross-volatility comparability).
- raw_tqi = normalised_slope * r_squared.
- smoothed_tqi = SMA(raw_tqi, smooth_period) (source's own final signal
  line).
- Long entry: smoothed_tqi crosses above 0 (source's LONG rule, long-only
  adaptation -- flat instead of short on the mirror-image SHORT signal,
  per this repo's existing long-only convention).
- Exit: smoothed_tqi crosses back below 0 (source's SHORT rule reused as
  an exit-to-flat trigger) OR after max_hold_days bars, whichever first.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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


def _atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def _rolling_slope_r2(close: pd.Series, length: int) -> tuple[pd.Series, pd.Series]:
    """Rolling OLS slope and R^2 of close vs. bar index over a window."""
    x = np.arange(length, dtype=float)
    x_mean = x.mean()
    x_centered = x - x_mean
    ss_xx = (x_centered ** 2).sum()

    n = len(close)
    slopes = np.full(n, np.nan)
    r2s = np.full(n, np.nan)
    close_vals = close.to_numpy()

    for i in range(length - 1, n):
        window_vals = close_vals[i - length + 1: i + 1]
        y_mean = window_vals.mean()
        y_centered = window_vals - y_mean
        ss_xy = (x_centered * y_centered).sum()
        slope = ss_xy / ss_xx if ss_xx != 0 else 0.0
        intercept = y_mean - slope * x_mean
        fitted = intercept + slope * x
        ss_res_fit = ((fitted - y_mean) ** 2).sum()
        ss_tot = (y_centered ** 2).sum()
        r2 = ss_res_fit / ss_tot if ss_tot != 0 else 0.0
        slopes[i] = slope
        r2s[i] = r2

    return pd.Series(slopes, index=close.index), pd.Series(r2s, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 20,
    atr_length: int = 14,
    smooth_period: int = 5,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    slope, r2 = _rolling_slope_r2(close, length)
    atr = _atr(df, atr_length)
    normalised_slope = slope / atr.replace(0.0, np.nan)
    raw_tqi = normalised_slope * r2
    smoothed_tqi = raw_tqi.rolling(smooth_period).mean()

    cross_up = (smoothed_tqi > 0) & (smoothed_tqi.shift(1) <= 0)
    cross_down = (smoothed_tqi < 0) & (smoothed_tqi.shift(1) >= 0)

    n = len(close)
    entries = cross_up.fillna(False).to_numpy()
    exit_signal = cross_down.fillna(False).to_numpy()

    position = np.zeros(n, dtype=int)
    in_pos = False
    entry_bar = -1
    for t in range(n):
        if entries[t] and not in_pos:
            in_pos = True
            entry_bar = t
        if in_pos:
            position[t] = 1
            held = t - entry_bar
            if exit_signal[t] or held >= max_hold_days:
                in_pos = False

    return pd.Series(position, index=close.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
