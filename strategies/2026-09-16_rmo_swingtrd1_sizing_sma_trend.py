"""Strategy: SMA(trend_window) directional gate with continuous Rahul
Mohindar Oscillator SwingTrd1 (range-normalized displacement) sizing
overlay + deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Rahul Mohindar Oscillator (Viratech India, official MetaStock inclusion
2006), per https://www.luxalgo.com/library/indicator/rahul-mohindar-oscillator/
(visited this iteration): "Ten simple moving averages are chained, each
2-period pass smoothing the one before, and price's displacement from
their average is normalized by the recent range to form SwingTrd 1. Two
30-period exponential smoothings of it yield SwingTrd 2 and SwingTrd 3,
while an 81-period EMA of SwingTrd 1 becomes the RMO itself." This repo
has 3 prior RMO entries, all using either the RAW (unnormalized)
close-minus-chained-MA displacement as the RMO bias line
(2026-09-05-004/2026-09-16-061) or the ST2-ST3 spread of that raw line
(2026-09-15-019). None have used SwingTrd 1 itself -- the intermediate,
RANGE-NORMALIZED displacement line ((close - MA10) / (HighestHigh(N) -
LowestLow(N))) that ST2/ST3/RMO are all built from. Being normalized by
its own recent range, ST1 is naturally bounded roughly in [-1, 1] by
construction (like %B or TD REI), distinct from the raw unnormalized RMO
line this repo already tested. This sub-iteration uses ST1 directly (no
z-score/tanh needed, only a clip to [-1,1] for safety) as a CONTINUOUS
SIZING dial inside an SMA(trend_window) uptrend gate with deadband. First
RMO-SwingTrd1 (range-normalized displacement) strategy in this repo.

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


def _rmo_swingtrd1(
    close: pd.Series, high: pd.Series, low: pd.Series, sma_period: int, range_lookback: int
) -> pd.Series:
    """SwingTrd1 = (close - chained_MA10) / (HighestHigh(range_lookback) -
    LowestLow(range_lookback)), per LuxAlgo's disclosed RMO reconstruction.
    """
    ma = close
    for _ in range(10):
        ma = ma.rolling(sma_period, min_periods=max(2, sma_period // 2)).mean()
    displacement = close - ma

    hh = high.rolling(range_lookback).max()
    ll = low.rolling(range_lookback).min()
    rng = (hh - ll).replace(0.0, np.nan)

    st1 = displacement / rng
    return st1.fillna(0.0)


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
    sma_period: int = 2,
    range_lookback: int = 10,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    ST1 is naturally bounded roughly [-1,1] by construction (range
    normalization) -- clipped for safety, used directly (no z-score/tanh
    needed) as a sizing dial: exposure = clip(base_exposure +
    sensitivity*dial, 0, cap), gated to 0 whenever close is below its
    SMA(trend_window).
    """
    df = _prep(price_df)
    close, high, low = df["close"], df["high"], df["low"]

    trend_long = close > close.rolling(trend_window).mean()
    st1 = _rmo_swingtrd1(close, high, low, sma_period, range_lookback)
    dial = st1.clip(lower=-1.0, upper=1.0)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    sma_period: int = 2,
    range_lookback: int = 10,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        sma_period=sma_period,
        range_lookback=range_lookback,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
