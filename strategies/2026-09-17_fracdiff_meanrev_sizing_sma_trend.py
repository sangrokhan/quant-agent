"""Strategy: SMA(trend_window) directional gate with continuous Fractional
Differentiation (FFD) mean-reversion sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per https://microalphas.com/fractional-differentiation (Marcos Lopez de
Prado, "Advances in Financial Machine Learning", 2018): raw price is
non-stationary (unit root), while ordinary first-differencing (returns) is
stationary but nearly memoryless. Fractional differentiation generalizes the
(1-B)^d differencing operator to a non-integer order d in (0,1), producing a
series that is stationary (a well-defined, mean-reverting series with finite
variance) while retaining much more of the level/trend "memory" than raw
returns. The source explicitly notes this is a feature-transformation
technique, not an alpha by itself -- so this strategy builds a genuinely new
mean-reversion signal on top of it: because the FFD series (using de Prado's
fixed-width-window weight truncation) is, unlike raw price, actually
stationary, "distance from its own rolling mean" is a well-defined
mean-reversion signal in a way it is NOT for raw price (which has no fixed
mean to revert to). This is distinct from every other distance-from-MA
sizing dial already in this repo (VAMA, FRAMA, KAMA, T3, DPO, Donchian
Width, RVI, etc.) -- all of those measure distance of RAW close price from
an adaptive moving-average baseline; this one instead z-scores the
FFD-transformed (order d) log-price series itself, then mean-reverts on
that, inside an SMA(trend_window) uptrend gate (only mean-revert against the
noise of an underlying uptrend, not falling knives) + deadband. First
fractional-differentiation-based strategy in this repo.

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


def _ffd_weights(d: float, threshold: float, max_len: int = 500) -> np.ndarray:
    """De Prado's fixed-width-window fractional-differencing weights.

    w_0 = 1; w_k = -w_{k-1} * (d - k + 1) / k
    Truncate once |w_k| < threshold (fixed-width window).
    """
    weights = [1.0]
    k = 1
    while k < max_len:
        w_k = -weights[-1] * (d - k + 1) / k
        if abs(w_k) < threshold:
            break
        weights.append(w_k)
        k += 1
    return np.array(weights)


def _frac_diff_ffd(series: pd.Series, d: float, threshold: float = 1e-4) -> pd.Series:
    """Apply de Prado's fixed-width-window fractional differencing to a series."""
    weights = _ffd_weights(d, threshold)
    width = len(weights)
    values = series.to_numpy()
    out = np.full(len(values), np.nan)
    for i in range(width - 1, len(values)):
        window = values[i - width + 1: i + 1][::-1]
        out[i] = np.dot(weights, window)
    return pd.Series(out, index=series.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ffd_d: float = 0.4,
    ffd_threshold: float = 1e-3,
    zscore_window: int = 60,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Log-price is fractionally differenced (order ffd_d, de Prado
    fixed-width-window weights truncated at ffd_threshold), rolling
    z-scored (zscore_window) and tanh-squashed to [-1,1] with sign flipped
    (mean-reversion: negative z -> long more), then used as a sizing dial
    inside an SMA(trend_window) uptrend gate.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    log_price = np.log(close.replace(0.0, np.nan))
    frac_diff = _frac_diff_ffd(log_price, ffd_d, ffd_threshold)

    roll_mean = frac_diff.rolling(zscore_window).mean()
    roll_std = frac_diff.rolling(zscore_window).std().replace(0.0, np.nan)
    z = (frac_diff - roll_mean) / roll_std
    dial = -np.tanh(z.fillna(0.0))  # mean reversion: negative z -> more long

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ffd_d: float = 0.4,
    ffd_threshold: float = 1e-3,
    zscore_window: int = 60,
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
        ffd_d=ffd_d,
        ffd_threshold=ffd_threshold,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
