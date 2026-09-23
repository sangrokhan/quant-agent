"""Strategy: SMA(fast/slow) crossover trend entry, gated by a rolling Hurst
exponent regime filter, exit via a percentage trailing stop.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-011):
Per PyQuantLab's "Can the Hurst Exponent Reliably Identify Price Trends?"
(https://pyquantlab.medium.com/can-the-hurst-exponent-reliably-identify-price-trends-4aaa14ad9dda),
a rolling-window Hurst exponent (estimated via classic Rescaled-Range (R/S)
analysis) above a threshold indicates a persistent/trending regime; only
taking a trend-following SMA-crossover entry when the market is confirmed
"trending" by Hurst should filter out whipsaw entries during random-walk or
mean-reverting regimes. The source used a symmetric long/short system with a
trailing-stop exit and no indicator-based exit signal; this repo restricts to
long-only (SAFETY.md) and adapts to a daily-bar QQQ/SPY/BTC/ETH universe
in place of the source's generic backtrader setup.

This is the first Hurst-exponent-family strategy in this repo (zero prior
entries in strategies_index.jsonl for "Hurst").

Signal logic
------------
- Hurst exponent H estimated via classic R/S analysis over a rolling
  `hurst_window` (default 100) on log returns, using window subdivisions
  [10, 20, sqrt(N), N/2] (points for the log-log R/S vs. lag regression).
- "Trending regime" when H > `hurst_threshold` (default 0.55-0.70 per
  source's own example runs).
- Trend signal: SMA(`sma_fast`) crosses above SMA(`sma_slow`).
- Entry (long): trending regime AND fresh fast-over-slow SMA cross-up
  (or already fast>slow while entering a fresh trending regime).
- Exit: percentage trailing stop (`trail_percent`, default 0.05) from the
  running peak close since entry -- the source's own exit mechanism, no
  indicator-based exit. Also force-flat if the regime stops being
  "trending" (source's implicit assumption the filter should hold) is
  NOT applied here -- we keep strictly to the source's disclosed trailing-
  stop-only exit to test that mechanism faithfully.

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


def _rs_hurst(log_returns: np.ndarray) -> float:
    """Classic Rescaled-Range Hurst exponent estimate for one window of
    log returns. Returns np.nan if the window is degenerate."""
    n = len(log_returns)
    if n < 20:
        return np.nan
    # window subdivisions to sample the log-log R/S vs lag relationship
    lags = sorted(set([10, 20, max(21, n // 4), max(22, n // 2), n]))
    lags = [l for l in lags if 10 <= l <= n]
    if len(lags) < 3:
        return np.nan

    log_lags = []
    log_rs = []
    for lag in lags:
        # split series into non-overlapping chunks of size `lag`, average R/S
        n_chunks = n // lag
        if n_chunks < 1:
            continue
        rs_vals = []
        for c in range(n_chunks):
            chunk = log_returns[c * lag:(c + 1) * lag]
            mean = chunk.mean()
            dev = chunk - mean
            cum_dev = np.cumsum(dev)
            r = cum_dev.max() - cum_dev.min()
            s = chunk.std(ddof=0)
            if s > 0:
                rs_vals.append(r / s)
        if rs_vals:
            log_lags.append(np.log(lag))
            log_rs.append(np.log(np.mean(rs_vals)))

    if len(log_lags) < 3:
        return np.nan
    slope, _ = np.polyfit(log_lags, log_rs, 1)
    return float(slope)


def _hurst_series(close: pd.Series, hurst_window: int, stride: int = 5) -> pd.Series:
    """Rolling Hurst exponent, computed every `stride` bars (R/S analysis is
    expensive) and forward-filled between recomputes -- a standard efficiency
    shortcut since H changes slowly given it's estimated over a long window."""
    log_ret = np.log(close / close.shift(1))
    arr = log_ret.values
    n = len(close)
    values = [np.nan] * n
    last = np.nan
    for i in range(hurst_window, n):
        if (i - hurst_window) % stride == 0:
            window = arr[i - hurst_window:i]
            window = window[~np.isnan(window)]
            last = _rs_hurst(window)
        values[i] = last
    return pd.Series(values, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    hurst_window: int = 100,
    hurst_threshold: float = 0.55,
    sma_fast: int = 20,
    sma_slow: int = 50,
    trail_percent: float = 0.05,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    hurst = _hurst_series(close, hurst_window)
    is_trending = hurst > hurst_threshold

    fast = close.rolling(sma_fast).mean()
    slow = close.rolling(sma_slow).mean()
    fast_above_slow = fast > slow

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    peak_close = None

    for i in range(len(close)):
        c = close.iloc[i]
        if in_position:
            if c > peak_close:
                peak_close = c
            stop_price = peak_close * (1 - trail_percent)
            if c <= stop_price:
                in_position = False
                position.iloc[i] = 0
                peak_close = None
                continue
            position.iloc[i] = 1
        else:
            trending_ok = bool(is_trending.iloc[i]) if not pd.isna(is_trending.iloc[i]) else False
            fas_ok = bool(fast_above_slow.iloc[i]) if not pd.isna(fast_above_slow.iloc[i]) else False
            if trending_ok and fas_ok:
                in_position = True
                peak_close = c
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
