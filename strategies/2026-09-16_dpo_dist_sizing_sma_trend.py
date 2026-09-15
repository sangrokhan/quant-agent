"""Strategy: SMA(trend_window) directional gate with continuous DPO
(Detrended Price Oscillator) distance sizing overlay + deadband,
leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-16-047, this cron trigger):
Detrended Price Oscillator (DPO): DPO = close[t - (N//2 + 1)] - SMA(N)[t],
i.e. the close price from N/2+1 periods ago minus the current N-period
simple moving average. This strips trend out of price so cyclical
overbought/oversold swings become visible (source:
https://www.quantifiedstrategies.com/detrended-price-oscillator/, visited
this iteration -- discrete counter-trend rule: buy when DPO crosses below
a -X% threshold, sell when DPO crosses above a +X% threshold; optimal
params found by source's own backtest were N=15, threshold=2.5% on a
multi-asset ETF portfolio). First DPO strategy in this repo (0 prior
entries for "DPO"/"Detrended Price Oscillator" in strategies_index.jsonl).

This iteration reuses this repo's established continuous-sizing-dial
pattern (cf. PMO 2026-09-15-045, RVI 2026-09-15-044) rather than the
source's literal discrete threshold-crossing trigger: DPO is normalized
by dividing by the SMA (percent-DPO), rolling z-scored, and tanh-squashed
into [-1,+1] as a continuous exposure-sizing dial, gated by an
SMA(trend_window) uptrend filter with a deadband to cut turnover. This
differs from the source's raw discrete counter-trend crossover, and from
every previously tested indicator family in this repo (novel indicator).

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


def _dpo(close: pd.Series, dpo_window: int) -> pd.Series:
    """DPO = close[t - (N//2 + 1)] - SMA(N)[t], normalized by SMA (percent DPO)."""
    shift = dpo_window // 2 + 1
    sma = close.rolling(dpo_window).mean()
    shifted_close = close.shift(shift)
    dpo = shifted_close - sma
    pct_dpo = dpo / sma.replace(0.0, np.nan)
    return pct_dpo


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
    dpo_window: int = 20,
    sensitivity: float = 0.5,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    leverage_cap: float = 1.0,
    deadband: float = 0.3,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Percent-DPO is rolling z-scored over `zscore_window` and tanh-squashed
    to [-1,+1] before use as a sizing dial, gated by an SMA(trend_window)
    uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    pct_dpo = _dpo(close, dpo_window)

    roll_mean = pct_dpo.rolling(zscore_window).mean()
    roll_std = pct_dpo.rolling(zscore_window).std()
    zscore = (pct_dpo - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    dpo_window: int = 20,
    sensitivity: float = 0.5,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    leverage_cap: float = 1.0,
    deadband: float = 0.3,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        dpo_window=dpo_window,
        sensitivity=sensitivity,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
