"""Strategy: SMA(trend_window) directional gate with continuous StochCMO
(Stochastic-of-Chande-Momentum-Oscillator) sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
StochCMO ("Stochastic CMO [SHK]", shayankm, TradingView, visited this
iteration: https://www.tradingview.com/scripts/stochcmo/): applies the
classic Stochastic Oscillator formula to a rolling window of Chande
Momentum Oscillator (CMO) VALUES instead of raw price -- i.e. it measures
where the current CMO reading sits relative to its own recent
high/low range, natively bounded [0,1]. Per the source's own description:
"gives traders an idea of whether the current CMO value is overbought or
oversold" and is used "similar to StochRSI", but built on CMO (a raw,
unsmoothed momentum measure per Tushar Chande, symmetric on up/down days,
distinct from RSI's average-gain/average-loss construction and reaching
extremes more often since CMO applies no internal smoothing) rather than
RSI. This repo has tested plain CMO (multiple binary-threshold entries),
StochRSI (multiple variants), and Stochastic-of-other-oscillators
(Stochastic Momentum Index) separately, but never Stochastic applied
specifically to CMO -- first StochCMO-specific construction in this repo.

This iteration reframes StochCMO as a CONTINUOUS SIZING dial (already
naturally bounded [0,1], rescaled to [-1,1] via 2x-1, no z-score/tanh
needed) used as an exposure multiplier inside an SMA(trend_window) uptrend
gate with a deadband to cut turnover, following this repo's repeatedly
validated continuous-sizing-dial pattern for oscillator families.

Source: https://www.tradingview.com/scripts/stochcmo/ (visited this
iteration, browser_exec after web_search returned an empty/garbage result
for the discovery query).

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


def _cmo(close: pd.Series, cmo_period: int) -> pd.Series:
    diff = close.diff()
    up = diff.clip(lower=0.0)
    down = (-diff).clip(lower=0.0)
    sum_up = up.rolling(cmo_period).sum()
    sum_down = down.rolling(cmo_period).sum()
    denom = (sum_up + sum_down).replace(0.0, np.nan)
    cmo = 100.0 * (sum_up - sum_down) / denom
    return cmo


def _stoch_cmo(cmo: pd.Series, stoch_period: int) -> pd.Series:
    lo = cmo.rolling(stoch_period).min()
    hi = cmo.rolling(stoch_period).max()
    rng = (hi - lo).replace(0.0, np.nan)
    stoch = (cmo - lo) / rng
    return stoch.clip(lower=0.0, upper=1.0)


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
    cmo_period: int = 14,
    stoch_period: int = 14,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    StochCMO (already naturally bounded [0,1]) is rescaled to [-1,+1] via
    2x-1 (no z-score/tanh needed since it's a native ratio) before use as a
    sizing dial, gated by an SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    cmo = _cmo(close, cmo_period)
    stoch_cmo = _stoch_cmo(cmo, stoch_period)
    dial = (2.0 * stoch_cmo.fillna(0.5)) - 1.0

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    cmo_period: int = 14,
    stoch_period: int = 14,
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
        cmo_period=cmo_period,
        stoch_period=stoch_period,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
