"""Strategy: SMA(trend_window) directional gate with continuous Prime
Number Bands %B sizing overlay + deadband, leverage-cap-aware for crypto
from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Prime Number Bands (Modulus Financial Engineering Inc.), per
https://www.quantifiedstrategies.com/prime-number-bands/ (found via
web_search, read via browser_exec -- the source explicitly states "we have
not written the code required to backtest it", i.e. no reference
implementation exists anywhere, but the calculation steps are fully
disclosed and mechanical): over a rolling window, find the prime number
NEAREST the window's highest high (upper band) and the prime number NEAREST
the window's lowest low (lower band). Similar in role to Bollinger Bands
(channel + overbought/oversold + slope-direction reading) but constructed
from prime-number proximity to price levels instead of a moving average +/-
standard deviation. Genuinely novel construction never tested in this repo
(0 prior "Prime Number Bands" entries).

This iteration applies the repo's established %B-in-channel continuous
sizing dial reframing (successfully used for STARC, Keltner, Bollinger,
Acceleration Bands, Elder AutoEnvelope, Standard Error Bands, Kirshenbaum
Bands):
    prime_pctb = (close - lower_prime) / (upper_prime - lower_prime)
naturally centered ~0.5 inside the band (can exceed [0,1] on band pierces),
rescaled via (pctb - 0.5) * 2 to a zero-centered dial, clipped to [-1, 1],
used as a sizing multiplier within an SMA(trend_window) uptrend gate.

Implementation note: "nearest prime number" is computed with a
segmented-sieve-free simple trial-division primality test (no numeric
approximation) -- suitable for daily-bar price magnitudes (tens to tens of
thousands), memoized per unique rounded price level to keep it fast across
a multi-year daily series.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True


@lru_cache(maxsize=200_000)
def _nearest_prime(value_rounded: int) -> int:
    """Nearest prime integer to `value_rounded` (ties broken toward the
    smaller candidate, i.e. search up and down in lockstep and return the
    first hit found stepping outward)."""
    if value_rounded < 2:
        return 2
    if _is_prime(value_rounded):
        return value_rounded
    offset = 1
    while True:
        lo = value_rounded - offset
        hi = value_rounded + offset
        if lo >= 2 and _is_prime(lo):
            return lo
        if _is_prime(hi):
            return hi
        offset += 1


def _prime_bands(df: pd.DataFrame, window: int) -> tuple[pd.Series, pd.Series]:
    """Upper band = nearest prime to rolling window's highest high;
    lower band = nearest prime to rolling window's lowest low."""
    high, low = df["high"], df["low"]
    rolling_high = high.rolling(window).max()
    rolling_low = low.rolling(window).min()

    upper = rolling_high.apply(
        lambda v: float(_nearest_prime(int(round(v)))) if pd.notna(v) else np.nan
    )
    lower = rolling_low.apply(
        lambda v: float(_nearest_prime(int(round(v)))) if pd.notna(v) else np.nan
    )
    return upper, lower


def _prime_pctb(df: pd.DataFrame, window: int) -> pd.Series:
    """Prime Number Bands %B: (close - lower_prime) / (upper_prime - lower_prime)."""
    close = df["close"]
    upper, lower = _prime_bands(df, window)
    band_width = (upper - lower).replace(0.0, np.nan)
    pctb = (close - lower) / band_width
    return pctb


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
    prime_window: int = 20,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Prime Number Bands %B is centered ~0.5; rescaled to a zero-centered dial
    via (pctb - 0.5) * 2, clipped to [-1, 1], then used as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    pctb = _prime_pctb(df, prime_window)
    pctb_centered = ((pctb - 0.5) * 2.0).clip(-1.0, 1.0)

    raw_exposure = base_exposure + sensitivity * pctb_centered
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    prime_window: int = 20,
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
        prime_window=prime_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
