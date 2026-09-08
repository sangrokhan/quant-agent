"""Strategy: Time Series Forecast (TSF) price-crossover, ADX(14)>threshold
trend-strength gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-052):
Per arrowalgo.com's TSF explainer (browser_exec fallback -- web_search
DuckDuckGo returned "No results found" for the first query), the Time
Series Forecast indicator draws a linear-regression best-fit line through
the last `n` closes and projects it one bar forward. Source's own
"Strategy 1: TSF Crossover Entry" explicit rule: long entry when price
crosses above the TSF line, exit when price crosses back below it -- and
the source's own explicit pairing recommendation is an ADX(14)>25
trend-strength filter ("pair this with an ADX filter... require ADX above
25 before taking crossover signals to confirm you trade only in genuine
trends") to avoid false signals in choppy/sideways markets, since a raw
price/TSF crossover "generates too many false signals" without it.

This is the FIRST Time Series Forecast strategy in this repo (0 prior hits
on "Time Series Forecast"/"TSF"/"Regression Coeff" in
strategies_index.jsonl) -- distinct from all prior ADX-gated strategies
(25 prior hits on "ADX") since none of them used a linear-regression
forecast-line crossover as the base signal.

Signal logic
------------
- TSF(n): fit an OLS line (slope, intercept) to the last `n` closes (x=0..
  n-1), evaluate at x=n (one bar beyond the window -- the "forecast").
- ADX(14) via standard Wilder smoothing of +DM/-DM/TR.
- Entry (long): close crosses above TSF AND ADX(14) > adx_threshold.
- Exit: close crosses back below TSF, OR ADX drops below adx_threshold
  (trend-strength filter breaks), OR a max_hold_days time-stop.

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


def _tsf(close: pd.Series, n: int) -> pd.Series:
    """Linear-regression forecast line, one bar beyond each rolling window."""
    x = np.arange(n, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    def _forecast(window: np.ndarray) -> float:
        y_mean = window.mean()
        slope = ((x - x_mean) * (window - y_mean)).sum() / x_var
        intercept = y_mean - slope * x_mean
        return intercept + slope * n  # one bar beyond the window (x=n)

    return close.rolling(n).apply(_forecast, raw=True)


def _adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(alpha=1 / n, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / atr
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1 / n, adjust=False).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    tsf_window: int = 14,
    adx_window: int = 14,
    adx_threshold: float = 25.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    tsf = _tsf(close, tsf_window)
    adx = _adx(df, adx_window)

    cross_up = (close > tsf) & (close.shift(1) <= tsf.shift(1))
    cross_down = (close < tsf) & (close.shift(1) >= tsf.shift(1))
    trend_ok = adx > adx_threshold

    entry_signal = cross_up & trend_ok

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = -1
    for i in range(len(close)):
        if not in_pos:
            es = entry_signal.iloc[i]
            if bool(es) if pd.notna(es) else False:
                in_pos = True
                entry_idx = i
                position.iloc[i] = 1
        else:
            held = i - entry_idx
            cd = cross_down.iloc[i]
            cd_bool = bool(cd) if pd.notna(cd) else False
            adx_break = adx.iloc[i] <= adx_threshold if pd.notna(adx.iloc[i]) else False
            if cd_bool or adx_break or held >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    tsf_window: int = 14,
    adx_window: int = 14,
    adx_threshold: float = 25.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no txn costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        tsf_window=tsf_window,
        adx_window=adx_window,
        adx_threshold=adx_threshold,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change()
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret.fillna(0.0)
