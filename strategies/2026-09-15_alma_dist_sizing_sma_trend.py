"""Strategy: SMA(trend_window) directional gate with continuous ALMA
(Arnaud Legoux Moving Average) distance sizing overlay + deadband,
leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-15-042, this cron trigger):
ALMA (Arnaud Legoux & Dimitrios Kouzis-Loukas, 2009), per LuxAlgo's guide
(https://www.luxalgo.com/blog/arnaud-legoux-moving-average-alma-guide/,
visited this iteration): a windowed FIR moving average whose weights
follow a Gaussian bell curve shifted toward the most recent bars. Given
window N, offset (default 0.85), sigma (default 6): peak m = offset*(N-1),
width s = N/sigma, weight w(i) = exp(-(i-m)^2 / (2*s^2)) for bar index i
in [0, N-1] (0=oldest, N-1=newest); ALMA = sum(w(i)*price(i)) / sum(w(i)).
Source's own framing: for a given amount of smoothing, ALMA shows less lag
than a simple moving average and less noise than an exponential moving
average, biased toward responsiveness via the offset parameter. First ALMA
strategy in this repo (0 prior entries for this indicator family).

Construction (following this repo's established "distance-from-adaptive-MA
sizing dial" pattern, cf. McGinley Dynamic, FRAMA, Gann HiLo distance
entries): normalized distance = (close - ALMA(window, offset, sigma)) /
ALMA, rolling z-scored and tanh-squashed into [-1,+1], used as a continuous
sizing dial inside an SMA(trend_window) uptrend gate, with a deadband to
cut turnover.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
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


def _alma(close: pd.Series, window: int, offset: float, sigma: float) -> pd.Series:
    """Arnaud Legoux Moving Average: Gaussian-weighted FIR smoother biased
    toward recent bars within each rolling window.
    """
    m = offset * (window - 1)
    s = window / sigma
    idx = np.arange(window)
    weights = np.exp(-((idx - m) ** 2) / (2.0 * s * s))
    weights = weights / weights.sum()

    values = close.to_numpy()
    n = len(values)
    out = np.full(n, np.nan)
    for t in range(window - 1, n):
        window_vals = values[t - window + 1 : t + 1]
        out[t] = np.dot(window_vals, weights)
    return pd.Series(out, index=close.index)


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    alma_window: int = 20,
    alma_offset: float = 0.85,
    alma_sigma: float = 6.0,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    close's normalized distance from ALMA(alma_window, alma_offset,
    alma_sigma) is rolling z-scored over `zscore_window` and tanh-squashed
    to [-1,+1] before use as a sizing dial, gated by an SMA(trend_window)
    uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    alma = _alma(close, alma_window, alma_offset, alma_sigma)
    distance = (close - alma) / alma.replace(0.0, np.nan)

    roll_mean = distance.rolling(zscore_window).mean()
    roll_std = distance.rolling(zscore_window).std()
    zscore = (distance - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    alma_window: int = 20,
    alma_offset: float = 0.85,
    alma_sigma: float = 6.0,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        alma_window=alma_window,
        alma_offset=alma_offset,
        alma_sigma=alma_sigma,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
