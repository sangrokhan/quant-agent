"""Strategy: SMA(trend_window) directional gate with continuous Firefly
Oscillator sizing overlay + deadband, leverage-cap-aware for crypto from
the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Firefly Oscillator (LuxAlgo, community-bred momentum gauge) -- confirmed
via https://www.luxalgo.com/library/indicator/firefly-oscillator/
(browser_exec navigation, web_search DDGS backend returned an empty/error
result for this query): weighted price = (High+Low+2*Close)/4 (double-
counts close); z-score that weighted price against its own rolling EMA
basis (default length 10) and rolling std; double-smooth the z-score with
a zero-lag EMA pass (default length 3); rescale so 50 is neutral on a
roughly 0-100 scale (unbounded z-score underneath means violent bars can
push slightly past 0/100 -- "stretch, not error", per source). This repo
has exactly 1 prior Firefly Oscillator entry (2026-09-09-058, a binary
midline(50)-crossover ENTRY trigger, accepted SPY-only, QQQ/crypto
rejected). That entry never used the oscillator's raw (0-100, 50-centered)
value as a continuous SIZING dial -- the same reframing pattern that has
repeatedly rescued binary-only bounded oscillators in this repo (BOP, CHOP,
VZO, ADX, DMI-diff, Vortex-diff-ratio, TSI, RMI, SMI, STARC %B-analog,
etc.). Economic rationale: the Firefly's z-scored + zero-lag-smoothed
stretch measures how far price has extended from its own recent
volatility-normalized basis; a persistently high reading (>50, stretched
bullish) signals sustained conviction warranting larger exposure within an
established uptrend, while a reading hugging 50 signals price sitting near
its own basis (low conviction) even while nominally above the SMA trend
filter. First Firefly Oscillator continuous-sizing variant.

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


def _firefly_raw(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    basis_length: int,
    smoothing_length: int,
) -> pd.Series:
    """Firefly Oscillator, per LuxAlgo's disclosed construction:
    weighted price -> z-score vs its own rolling EMA basis/std -> zero-lag
    double-smoothed EMA -> rescaled to a ~0-100 scale (50 = neutral).
    """
    weighted_price = (high + low + 2.0 * close) / 4.0

    basis = weighted_price.ewm(span=basis_length, adjust=False).mean()
    dev = weighted_price.rolling(basis_length).std().replace(0.0, np.nan)
    zscore = (weighted_price - basis) / dev

    # Zero-lag double-smoothing pass: EMA of (2*EMA - EMA(EMA)) removes lag.
    ema1 = zscore.ewm(span=smoothing_length, adjust=False).mean()
    ema2 = ema1.ewm(span=smoothing_length, adjust=False).mean()
    zero_lag = 2 * ema1 - ema2
    smoothed = zero_lag.ewm(span=smoothing_length, adjust=False).mean()

    # Rescale: 50 = neutral (zscore 0), roughly +/-2.5 std maps to 0/100.
    firefly = (smoothed * 20.0 + 50.0).fillna(50.0)
    return firefly


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
    basis_length: int = 10,
    smoothing_length: int = 3,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Firefly Oscillator (0-100, 50=neutral) is rescaled to [-1,+1] around
    its midline and used directly as a sizing dial, within an
    SMA(trend_window) uptrend gate.
    """
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    firefly = _firefly_raw(high, low, close, basis_length, smoothing_length)
    dial = ((firefly - 50.0) / 50.0).clip(lower=-1.0, upper=1.0)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    basis_length: int = 10,
    smoothing_length: int = 3,
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
        basis_length=basis_length,
        smoothing_length=smoothing_length,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
