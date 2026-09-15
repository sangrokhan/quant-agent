"""Strategy: SMA(trend_window) directional gate with continuous VWAP-deviation
sizing overlay + deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per https://www.quantifiedstrategies.com/vwap-trading-strategy/ (VWAP =
volume-weighted average price benchmark; the source's own backtests show
short-lookback price-vs-VWAP-MA deviations mean-revert while long-lookback
deviations trend), this repo's ledger already has 4 prior VWAP entries --
a rolling-band mean-reversion trigger (2026-09-04-052, rejected decisively),
an Anchored VWAP crossover + ATR-stop variant (2026-09-04-138/2026-09-06-164,
equity near-miss/crypto rejected), and a trend-continuation pullback
(2026-09-08-128, equity near-miss/crypto rejected) -- but NONE has reframed
the VWAP-deviation itself as a CONTINUOUS SIZING dial, the pattern this repo
has repeatedly found rescues binary-threshold VWAP-family near-misses for
other indicators (Amihud, Corwin-Schultz, VPCI, REX Oscillator, BVC).

This strategy computes a rolling N-day VWAP (volume-weighted mean of close
over `vwap_window`), takes the relative deviation (close - VWAP) / VWAP,
rolling-z-scores it over `zscore_window`, and tanh-squashes to [-1, 1] as a
continuous exposure dial (positive deviation = price running ahead of its
volume-weighted average = bullish momentum confirmation, consistent with
the source's finding that price above a rising VWAP tends to continue)
inside an SMA(trend_window) uptrend gate with a deadband to cut turnover.
First VWAP-as-continuous-sizing-dial strategy in this repo.

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


def _rolling_vwap(df: pd.DataFrame, window: int) -> pd.Series:
    close = df["close"]
    volume = df["volume"]
    pv = (close * volume).rolling(window).sum()
    v = volume.rolling(window).sum().replace(0, np.nan)
    return pv / v


def _vwap_deviation_signal(
    df: pd.DataFrame, vwap_window: int, zscore_window: int
) -> pd.Series:
    """tanh(rolling z-score of relative (close-VWAP)/VWAP deviation),
    bounded [-1, 1]."""
    close = df["close"]
    vwap = _rolling_vwap(df, vwap_window)
    rel_dev = (close - vwap) / vwap.replace(0, np.nan)

    roll_mean = rel_dev.rolling(zscore_window).mean()
    roll_std = rel_dev.rolling(zscore_window).std().replace(0, np.nan)
    zscore = (rel_dev - roll_mean) / roll_std

    return np.tanh(zscore.fillna(0.0))


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
    vwap_window: int = 20,
    zscore_window: int = 100,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    exposure = clip(base_exposure + sensitivity*dial, 0, cap), gated to 0
    whenever close is below its SMA(trend_window).
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    dial = _vwap_deviation_signal(df, vwap_window=vwap_window, zscore_window=zscore_window)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    vwap_window: int = 20,
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
        vwap_window=vwap_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
