"""Strategy: SMA(trend_window) directional gate with continuous
Fractal Adaptive Moving Average (FRAMA) distance sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
FRAMA (John Ehlers, per mesasoftware.com/papers/FRAMA.pdf and
MetaTrader5/theforexgeek): an adaptive EMA whose smoothing factor is driven
by the price series' fractal dimension D, estimated from high/low ranges
over two half-windows vs. the full window:
    N1 = (max(High,N/2 first half) - min(Low,N/2 first half)) / (N/2)
    N2 = (max(High,N/2 second half) - min(Low,N/2 second half)) / (N/2)
    N3 = (max(High,N) - min(Low,N)) / N
    D = (log(N1+N2) - log(N3)) / log(2)
    alpha = exp(-4.6 * (D - 1)), clipped to [0.01, 1.0]
    FRAMA_t = alpha * Close_t + (1 - alpha) * FRAMA_{t-1}
This repo has 9 prior FRAMA entries, ALL binary (breakout/crossover/slope
confirmation triggers off FRAMA vs price/other MAs), several close
near-misses. None used the normalized distance between price and FRAMA as
a CONTINUOUS SIZING dial. This iteration: (Close - FRAMA) / FRAMA, rolling
z-scored + tanh-squashed to [-1,+1], used as a sizing multiplier within an
SMA(trend_window) uptrend gate, deadband + leverage_cap for crypto.
Rationale: FRAMA already adapts its own lag to trend/chop conditions, so
price's normalized distance from it should be a cleaner momentum-strength
proxy than a fixed-lag MA distance. First FRAMA continuous-sizing variant.

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


def _frama(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    """Fractal Adaptive Moving Average (Ehlers). `window` must be even."""
    n = len(close)
    half = window // 2
    high_v = high.to_numpy()
    low_v = low.to_numpy()
    close_v = close.to_numpy()

    frama = np.full(n, np.nan)
    for i in range(window - 1, n):
        seg_high = high_v[i - window + 1: i + 1]
        seg_low = low_v[i - window + 1: i + 1]

        h1, l1 = seg_high[:half], seg_low[:half]
        h2, l2 = seg_high[half:], seg_low[half:]

        n1 = (h1.max() - l1.min()) / half
        n2 = (h2.max() - l2.min()) / half
        n3 = (seg_high.max() - seg_low.min()) / window

        if n1 > 0 and n2 > 0 and n3 > 0:
            d = (np.log(n1 + n2) - np.log(n3)) / np.log(2.0)
        else:
            d = 1.0
        alpha = np.exp(-4.6 * (d - 1.0))
        alpha = min(max(alpha, 0.01), 1.0)

        prev = frama[i - 1] if i > window - 1 and not np.isnan(frama[i - 1]) else close_v[i]
        frama[i] = alpha * close_v[i] + (1 - alpha) * prev

    return pd.Series(frama, index=close.index)


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
    frama_window: int = 16,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Normalized distance (Close - FRAMA) / FRAMA is rolling-z-scored over
    `zscore_window` bars and tanh-squashed to [-1,+1] before use as a
    sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    trend_long = close > close.rolling(trend_window).mean()
    frama = _frama(high, low, close, frama_window)
    dist = (close - frama) / frama.replace(0.0, np.nan)

    roll_mean = dist.rolling(zscore_window).mean()
    roll_std = dist.rolling(zscore_window).std()
    zscore = (dist - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    frama_window: int = 16,
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
        frama_window=frama_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
