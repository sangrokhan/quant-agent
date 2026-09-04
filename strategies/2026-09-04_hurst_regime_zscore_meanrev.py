"""Strategy: Z-score mean reversion, gated by a LOW rolling Hurst exponent
(anti-persistent regime) filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-156):
The rolling Hurst exponent (R/S rescaled-range analysis) measures
long-range persistence: H < 0.5 indicates anti-persistent/mean-reverting
behavior (per FractalCycles' Hurst exponent guide, "many popular
indicators like RSI assume mean-reverting behavior... When [H] is low,
they gain structural support"). The plain z-score mean-reversion strategy
already tested in this repo (2026-09-04-082: z<-2 long entry, exit at
z>=0) was rejected across ALL symbols with no regime awareness at all --
this iteration directly addresses that rejection by only trading the same
z-score entry when the market is confirmed to be in a mean-reverting
regime (H < hurst_threshold, e.g. 0.45), the theoretically-motivated
inverse pairing of the trend-following x high-Hurst strategy already
tested and rejected (2026-09-04-155).

Signal logic
------------
- Rolling Hurst exponent H over `hurst_window` bars (same R/S estimator as
  2026-09-04-155's strategy module, computed every `step` bars +
  forward-filled for performance).
- Mean-reverting regime: H < hurst_threshold (default 0.45).
- Z-score of close vs its own rolling SMA/STD over `zscore_window`.
- Long entry: z-score crosses below -entry_z_threshold AND we are in a
  mean-reverting regime (H < hurst_threshold).
- Exit: z-score reverts back above 0 (mean reached), OR the regime flips
  to non-mean-reverting (H >= hurst_threshold), OR a max_hold_days
  time-stop.
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
    hurst_threshold: float = 0.45,
    zscore_window: int = 20,
    entry_z_threshold: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    hurst = _rolling_hurst(close, hurst_window)
    mean_reverting_regime = hurst < hurst_threshold

    sma = close.rolling(zscore_window).mean()
    std = close.rolling(zscore_window).std()
    zscore = (close - sma) / std

    entry = (zscore < -entry_z_threshold) & mean_reverting_regime.fillna(False)
    exit_mean_reached = zscore >= 0
    exit_regime_flip = ~mean_reverting_regime.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_mean_reached.iloc[i]) or bool(exit_regime_flip.iloc[i]) or held >= max_hold_days:
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
