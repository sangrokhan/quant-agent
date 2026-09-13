"""Strategy: SMA200 trend-following gate with continuous Chande Momentum
Oscillator (CMO) sizing overlay.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-13-076):
CMO (Tushar Chande, 1994) = 100 * (SumUp - SumDown) / (SumUp + SumDown) over
a lookback window, naturally bounded in [-100, 100] (per howtotrade.com /
theforexgeek.com / quantifiedstrategies.com CMO explainers surfaced via
web_search this iteration). This repo has 4+ prior CMO entries, all using it
as a binary threshold-cross (+-50), signal-line-cross, or trend-pullback
ENTRY trigger -- all rejected. This iteration instead reuses the "bounded
oscillator as continuous sizing dial" pattern that has produced multiple
accepted strategies this cron trigger (Bollinger %B 2026-09-13-071, Aroon
Oscillator 2026-09-13-072, Williams %R 2026-09-13-074): scale exposure
continuously with CMO's own bounded value on the SMA(200) trend gate,
instead of firing discrete entry/exit signals off a fixed threshold cross.
Because CMO is symmetric around 0 (unlike %B/Williams %R's asymmetric
construction), exposure = clip(base_exposure + cmo_sensitivity *
(cmo/100.0), 0, leverage_cap) -- increase exposure as momentum strengthens
within the uptrend, reduce it as momentum fades toward/below zero, while the
SMA(200) gate still keeps the strategy flat outside the broader uptrend.
First CMO-as-continuous-sizing strategy in this repo.

Signal logic
------------
- Base directional signal: long-candidate when close > SMA(trend_window).
- CMO over `cmo_window`.
- Exposure while trend_long: clip(base_exposure + cmo_sensitivity *
  (cmo / 100.0), 0, leverage_cap).

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


def _cmo(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0.0)
    down = (-delta).clip(lower=0.0)
    sum_up = up.rolling(window).sum()
    sum_down = down.rolling(window).sum()
    denom = (sum_up + sum_down).replace(0, np.nan)
    cmo = 100.0 * (sum_up - sum_down) / denom
    return cmo


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    cmo_window: int = 14,
    base_exposure: float = 0.8,
    cmo_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    cmo = _cmo(close, cmo_window)

    raw_exposure = base_exposure + cmo_sensitivity * (cmo / 100.0)
    exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap).fillna(0.0)

    position = exposure.where(trend_long.fillna(False), other=0.0)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    cmo_window: int = 14,
    base_exposure: float = 0.8,
    cmo_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        cmo_window=cmo_window,
        base_exposure=base_exposure,
        cmo_sensitivity=cmo_sensitivity,
        leverage_cap=leverage_cap,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
