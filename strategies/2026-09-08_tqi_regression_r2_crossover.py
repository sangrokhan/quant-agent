"""Strategy: Trend Quality Indicator (TQI) -- ATR-normalized regression
slope weighted by R-squared, zero-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-054):
Per a TradingView open-source script description (read in-browser --
web_extract failed on the primary trendspider.com KB page with the
DuckDuckGo search-only-backend error, so fell back to browser_exec; the
trendspider.com page itself turned out too generic/no explicit rule, so
the TradingView TQI script page -- found via the same web_search results
list -- was used instead as the concrete source), the Trend Quality
Indicator combines a linear-regression slope (fit to closes over a
lookback window) normalized by ATR, multiplied by the regression's
R-squared (goodness-of-fit, 0=no linear fit/choppy, 1=perfect linear
fit) -- explicitly designed to "penalize trends that are not linear (i.e.
choppy or curved moves)". Source's own explicit rule: smoothed TQI
(SMA of the raw TQI) crossing above zero = long entry; trend state
persists until the next zero-line crossover (exit).

First R-squared-weighted trend-strength strategy in this repo -- distinct
from all prior plain-linear-regression-slope strategies (e.g.
2026-09-04-058) and from ADX/Choppiness/VHF trend-strength gates since TQI
directly multiplies the slope by the regression's own fit quality rather
than gating with a separate oscillator.

Signal logic
------------
- Regression slope over `n` bars: OLS fit of close vs bar-index (0..n-1),
  slope in price-per-bar units.
- R-squared: 1 - SS_res/SS_tot for the same fit.
- ATR(atr_window) for normalization.
- Raw TQI = (slope / ATR) * R_squared
- Smoothed TQI = SMA(raw TQI, smooth_window)
- Entry (long): smoothed TQI crosses above 0.
- Exit: smoothed TQI crosses back below 0, OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr


def _slope_and_r2(close: pd.Series, n: int) -> tuple[pd.Series, pd.Series]:
    x = np.arange(n, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    def _slope(window: np.ndarray) -> float:
        y_mean = window.mean()
        return ((x - x_mean) * (window - y_mean)).sum() / x_var

    def _r2(window: np.ndarray) -> float:
        y_mean = window.mean()
        slope = ((x - x_mean) * (window - y_mean)).sum() / x_var
        intercept = y_mean - slope * x_mean
        fitted = intercept + slope * x
        ss_res = ((window - fitted) ** 2).sum()
        ss_tot = ((window - y_mean) ** 2).sum()
        if ss_tot <= 0:
            return 0.0
        return 1.0 - ss_res / ss_tot

    slope = close.rolling(n).apply(_slope, raw=True)
    r2 = close.rolling(n).apply(_r2, raw=True)
    return slope, r2


def generate_signals(
    price_df: pd.DataFrame,
    reg_window: int = 20,
    atr_window: int = 14,
    smooth_window: int = 5,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    slope, r2 = _slope_and_r2(close, reg_window)
    tr = _true_range(df)
    atr = tr.rolling(atr_window).mean()

    raw_tqi = (slope / atr.replace(0, np.nan)) * r2
    tqi = raw_tqi.rolling(smooth_window).mean()

    cross_up = (tqi > 0) & (tqi.shift(1) <= 0)
    cross_down = (tqi < 0) & (tqi.shift(1) >= 0)

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = -1
    for i in range(len(close)):
        if not in_pos:
            cu = cross_up.iloc[i]
            if bool(cu) if pd.notna(cu) else False:
                in_pos = True
                entry_idx = i
                position.iloc[i] = 1
        else:
            held = i - entry_idx
            cd = cross_down.iloc[i]
            cd_bool = bool(cd) if pd.notna(cd) else False
            if cd_bool or held >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    reg_window: int = 20,
    atr_window: int = 14,
    smooth_window: int = 5,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no txn costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        reg_window=reg_window,
        atr_window=atr_window,
        smooth_window=smooth_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change()
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret.fillna(0.0)
