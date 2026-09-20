"""Strategy: Robust MAD-scaled z-score outlier mean-reversion, trend-gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-210):
Source: https://metricgate.com/docs/mad-scaled-z-score/ ("MAD-Scaled Z-Score:
Robust Outlier Detection", May 2026). Defines the robust (median/MAD-based)
z-score for a data point x_i as:
    z_i = (x_i - median(x)) / (1.4826 * MAD(x))
    MAD(x) = median(|x_i - median(x)|)
This is a robust alternative to the classical mean/std z-score for outlier
detection: median/MAD have a 50% breakdown point and resist "masking" (where
a handful of extreme observations inflate the classical std itself, hiding
their own extremity). Standard outlier threshold |z| >= 3 (Iglewicz-Hoaglin).
This repo has many classical-z-score (mean/std) mean-reversion/oscillator
strategies but none using the median/MAD robust variant.

Applied here: compute the rolling MAD-scaled z-score of daily returns. A
strongly negative outlier day (z <= -entry_z) is flagged as a robust
"outlier down day"; go long expecting reversion, but ONLY when price is
already above its long-term trend (SMA(trend_window)) -- consistent with
this repo's repeated finding that raw mean-reversion signals need a trend
filter to survive validation (e.g. rsi2_meanrev_trend200,
bb_meanrev_qqq_volregime).

Signal logic
------------
- daily_ret = pct_change(close).
- rolling_median = daily_ret.rolling(mad_window).median()
- rolling_mad = daily_ret.rolling(mad_window).apply(median absolute
  deviation from the window's own median)
- robust_z = (daily_ret - rolling_median) / (1.4826 * rolling_mad)
- uptrend = close > SMA(trend_window)
- Entry (long): robust_z <= -entry_z AND uptrend
- Exit: robust_z reverts toward 0 (>= exit_z, a less negative threshold,
  hysteresis) OR uptrend flips OR max_hold_days elapses.
- Flat otherwise.

Interface contract (validation/grid_test.py, validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def _rolling_mad(x: np.ndarray) -> float:
    med = np.median(x)
    return float(np.median(np.abs(x - med)))


def generate_signals(
    price_df: pd.DataFrame,
    mad_window: int = 40,
    entry_z: float = 3.0,
    exit_z: float = -1.0,
    trend_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    daily_ret = close.pct_change()
    rolling_median = daily_ret.rolling(mad_window).median()
    rolling_mad = daily_ret.rolling(mad_window).apply(_rolling_mad, raw=True)
    denom = 1.4826 * rolling_mad
    robust_z = (daily_ret - rolling_median) / denom.replace(0, np.nan)

    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    entry = (robust_z <= -entry_z) & uptrend.fillna(False)
    exit_revert = robust_z >= exit_z
    exit_trend_flip = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            revert = bool(exit_revert.iloc[i]) if not pd.isna(exit_revert.iloc[i]) else False
            flip = bool(exit_trend_flip.iloc[i]) if not pd.isna(exit_trend_flip.iloc[i]) else False
            if revert or flip or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            trig = bool(entry.iloc[i]) if not pd.isna(entry.iloc[i]) else False
            if trig:
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
