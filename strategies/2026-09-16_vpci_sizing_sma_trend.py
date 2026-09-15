"""Strategy: SMA(trend_window) directional gate with continuous Volume Price
Confirmation Indicator (VPCI, LazyBear) sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
LazyBear's Volume Price Confirmation Indicator (VPCI, TradingView 2015),
already implemented in this repo
(strategies/2026-09-08_vpci_trend_confirmation_crossover.py, id
2026-09-08-030), per https://pineify.app/pine-script/indicators/vpci
(already visited/logged in this repo's ledger; formula re-used unchanged,
no new fetch this iteration):

    VPC = VWMA(close, long_term) - SMA(close, long_term)
    VPR = VWMA(close, short_term) / SMA(close, short_term)
    VM  = SMA(volume, short_term) / SMA(volume, long_term)
    VPCI = VPC * VPR * VM

"A positive number means price is above its volume-weighted average, which
is bullish... positive confirms bulls are in control, negative confirms
bears." VPCI is the PRODUCT of three separately-meaningful sub-components
(a VWMA-vs-SMA price-confirmation term, a short/long VWMA-vs-SMA ratio
term, and a short/long volume-ratio term) rather than a difference-of-
moving-averages or cumulative sum -- distinct construction from every
other volume-price indicator already reframed as a continuous sizing dial
in this repo (Klinger, MFI, CMF, OBV, Elder Force Index, VWM).

This repo has 2 prior VPCI entries, both binary (zero-line-crossover
2026-09-08-030 rejected decisively; ADX+TTI+VPCI combined system
2026-09-12-169 rejected decisively), NEITHER used as a continuous sizing
dial. This iteration reframes the identical VPCI formula that way:
exposure scales with VPCI's own rolling-z-scored, tanh-squashed value,
inside an SMA(trend_window) uptrend gate -- following this cron trigger's
established continuous-sizing-dial pattern. First VPCI-as-continuous-
sizing-dial strategy in this repo.

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


def _vwma(price: pd.Series, volume: pd.Series, window: int) -> pd.Series:
    pv = (price * volume).rolling(window).sum()
    v = volume.rolling(window).sum().replace(0, np.nan)
    return pv / v


def _vpci(df: pd.DataFrame, short_term: int, long_term: int, ma_length: int) -> pd.Series:
    close = df["close"]
    volume = df["volume"]

    vpc = _vwma(close, volume, long_term) - close.rolling(long_term).mean()
    vpr = _vwma(close, volume, short_term) / close.rolling(short_term).mean().replace(0, np.nan)
    vm = volume.rolling(short_term).mean() / volume.rolling(long_term).mean().replace(0, np.nan)

    vpci = vpc * vpr * vm
    vpci_smoothed = vpci.rolling(ma_length).mean()
    return vpci_smoothed


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
    short_term: int = 5,
    long_term: int = 20,
    ma_length: int = 8,
    zscore_window: int = 100,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Raw VPCI is unbounded, so it's rolling-z-scored over `zscore_window`
    bars and squashed with tanh to [-1,+1] before being used as a sizing
    dial: exposure = clip(base_exposure + sensitivity*dial, 0, cap), gated
    to 0 whenever close is below its SMA(trend_window).
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    raw_vpci = _vpci(df, short_term, long_term, ma_length)

    roll_mean = raw_vpci.rolling(zscore_window).mean()
    roll_std = raw_vpci.rolling(zscore_window).std()
    zscore = (raw_vpci - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)
    raw_exposure = raw_exposure.where(~zscore.isna(), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    short_term: int = 5,
    long_term: int = 20,
    ma_length: int = 8,
    zscore_window: int = 100,
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
        short_term=short_term,
        long_term=long_term,
        ma_length=ma_length,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
