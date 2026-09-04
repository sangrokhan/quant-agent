"""Strategy: EMA crossover trend-following, gated by a rolling Hurst
exponent (R/S analysis) trending-regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-155):
The Hurst exponent H (Harold Hurst, 1951, Rescaled-Range / R/S analysis)
measures long-range persistence in a time series: H > 0.5 indicates
persistent/trending behavior, H < 0.5 indicates anti-persistent/
mean-reverting behavior, H ~= 0.5 indicates a random walk with no
exploitable structure. Per FractalCycles' Hurst exponent guide, trend-
following indicators are structurally favored when H is elevated and
structurally disfavored (whipsaw-prone) when H is low/near-random. This
strategy computes a ROLLING H via simplified R/S analysis and only takes
a classic fast/slow EMA crossover trend-following signal when H exceeds a
threshold (confirmed trending regime), staying flat otherwise -- distinct
from every prior trend-regime filter in this repo (VHF, ADX, Choppiness
Index, RWI) which all measure trend STRENGTH from price range/ATR ratios;
Hurst instead measures statistical LONG-MEMORY/PERSISTENCE via rescaled-
range scaling, a fundamentally different (fractal/statistical) construction.

Signal logic
------------
- Rolling Hurst exponent over `hurst_window` bars: split the window into
  `n_subseries` non-overlapping sub-periods, compute the classic R/S
  statistic (range of cumulative mean-centered deviations / std) per
  sub-period at 2-4 different sub-period lengths, then estimate H as the
  slope of log(R/S) vs log(sub-period length) (least-squares fit) -- the
  standard simplified R/S Hurst estimator.
- Trending regime: H > hurst_threshold (default 0.55).
- Long entry: fast EMA crosses above slow EMA AND we are in a trending
  regime (H > hurst_threshold).
- Exit: fast EMA crosses back below slow EMA, OR the regime flips to
  non-trending (H <= hurst_threshold), OR a max_hold_days time-stop.
- Flat (no position) whenever not in an active long.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series {0,1} position series
    generate_returns(price_df, **params) -> pd.Series daily strategy returns
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


def _rs_stat(series: np.ndarray) -> float:
    """Classic Rescaled Range (R/S) statistic for one sub-series."""
    n = len(series)
    if n < 2:
        return np.nan
    mean = series.mean()
    deviations = series - mean
    cumulative = np.cumsum(deviations)
    r = cumulative.max() - cumulative.min()
    s = series.std(ddof=0)
    if s == 0 or np.isnan(s):
        return np.nan
    return r / s


def _hurst_exponent(window_returns: np.ndarray, sub_lengths) -> float:
    """Estimate H via simplified R/S analysis: slope of log(R/S) vs
    log(sub-period length), averaging R/S across all non-overlapping
    sub-periods of each candidate length.
    """
    n = len(window_returns)
    log_lengths = []
    log_rs = []
    for length in sub_lengths:
        if length >= n or length < 8:
            continue
        n_chunks = n // length
        if n_chunks < 1:
            continue
        rs_values = []
        for i in range(n_chunks):
            chunk = window_returns[i * length : (i + 1) * length]
            rs = _rs_stat(chunk)
            if not np.isnan(rs) and rs > 0:
                rs_values.append(rs)
        if rs_values:
            log_lengths.append(np.log(length))
            log_rs.append(np.log(np.mean(rs_values)))
    if len(log_lengths) < 2:
        return np.nan
    slope, _ = np.polyfit(log_lengths, log_rs, 1)
    return float(slope)


def _rolling_hurst(close: pd.Series, hurst_window: int, n_subseries: int = 4, step: int = 5) -> pd.Series:
    """Rolling Hurst exponent, computed every `step` bars for speed and
    forward-filled in between (H changes slowly bar-to-bar for a
    100+-bar window, so this is a reasonable/standard performance
    optimization -- doesn't change the underlying R/S methodology,
    just how often it's re-evaluated).
    """
    log_ret = np.log(close / close.shift(1))
    sub_lengths = sorted({max(8, hurst_window // k) for k in range(1, n_subseries + 1)})

    values = [np.nan] * len(close)
    ret_arr = log_ret.values
    for i in range(hurst_window, len(close), step):
        window = ret_arr[i - hurst_window : i]
        window = window[~np.isnan(window)]
        if len(window) < hurst_window // 2:
            continue
        values[i] = _hurst_exponent(window, sub_lengths)
    result = pd.Series(values, index=close.index)
    return result.ffill()


def generate_signals(
    price_df: pd.DataFrame,
    hurst_window: int = 100,
    hurst_threshold: float = 0.55,
    fast_span: int = 20,
    slow_span: int = 50,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    hurst = _rolling_hurst(close, hurst_window)
    trending_regime = hurst > hurst_threshold

    fast_ema = close.ewm(span=fast_span, adjust=False).mean()
    slow_ema = close.ewm(span=slow_span, adjust=False).mean()
    bullish_cross = (fast_ema > slow_ema) & (fast_ema.shift(1) <= slow_ema.shift(1))
    bearish_cross = (fast_ema < slow_ema) & (fast_ema.shift(1) >= slow_ema.shift(1))

    entry = bullish_cross & trending_regime.fillna(False)
    exit_cross = bearish_cross
    exit_regime_flip = ~trending_regime.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or bool(exit_regime_flip.iloc[i]) or held >= max_hold_days:
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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
