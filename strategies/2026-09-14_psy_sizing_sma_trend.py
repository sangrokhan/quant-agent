"""Strategy: SMA(trend_window) directional gate with continuous
Psychological Line (PSY) sizing overlay + deadband, leverage-cap-aware for
crypto from the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Psychological Line (PSY): the percentage of the last N bars that closed
higher than the prior close, PSY = (count of up-closes in rolling N-bar
window / N) * 100 -- naturally bounded [0, 100] by construction, a pure
"win-rate/hit-rate" oscillator counting only the SIGN of each bar-to-bar
change, not its magnitude (distinct construction from magnitude-based
oscillators like RSI/RAVI). Per LuxAlgo
(https://www.luxalgo.com/library/indicator/psychological-line/, visited
this iteration via browser_exec after web_search's DDGS backend returned
no results for the query).

This repo's prior PSY entry (2026-09-08-076) used PSY as an OVERSOLD MEAN-
REVERSION threshold trigger (long below oversold_threshold, exit above
exit_threshold) and was REJECTED for weak/inconsistent grid pass_fraction
(0.076, crypto decisively 0/72). This iteration reframes PSY entirely: use
it as a CONTINUOUS SIZING dial (rescaled from [0,100] to [-1,+1], no
z-scoring/min-max window needed since it's already bounded) within the
existing SMA(trend_window) uptrend gate -- following this cron trigger's
validated continuous-sizing-dial pattern for other naturally-bounded
oscillators (RAVI, CTI, Kase Permission Stochastic), which has proven
robust against the parameter-sensitivity/pass-fraction failures that sank
threshold-based PSY.

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


def _psy(close: pd.Series, period: int = 12) -> pd.Series:
    """PSY = 100 * (count of up-closes in rolling `period`-bar window / period).

    Bounded [0, 100] by construction.
    """
    up = (close.diff() > 0).astype(float)
    return 100.0 * up.rolling(period).mean()


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
    psy_period: int = 12,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    PSY is bounded [0,100] by construction; rescaled to [-1,+1] via
    (PSY-50)/50 (centered on the 50% balance line, per the source's own
    interpretation), then used directly as a sizing dial -- no additional
    normalization window needed.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    psy = _psy(close, psy_period)
    psy_centered = (psy - 50.0) / 50.0  # rescale [0,100] -> [-1,+1]

    raw_exposure = base_exposure + sensitivity * psy_centered
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    psy_period: int = 12,
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
        psy_period=psy_period,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
