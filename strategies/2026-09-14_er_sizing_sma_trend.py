"""Strategy: SMA(trend_window) directional gate with continuous Kaufman
Efficiency Ratio (ER) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-111):
Kaufman Efficiency Ratio (Perry Kaufman, core component of KAMA):
ER = |NetChange(N)| / Volatility(N), where NetChange = |close - close.shift(N)|
and Volatility = sum(|close.diff()|) over the same N periods, natively
bounded [0, 1]. ER near 1 = smooth directional trend (net change ~ total
path traveled); ER near 0 = choppy/range-bound (large round-trip swings,
little net progress). Confirmed via Google AI overview (browser_exec
navigation).

Structurally this is the SAME unsigned trend-efficiency construction family
as VHF (net-move / total-path-length ratio) -- VHF uses
(highest_close-lowest_close) as its numerator while ER uses
|close-close.shift(N)|, a subtly different but closely related "net
displacement vs. total distance traveled" measure. VHF/PFE/RWI-diff/CHOP
(this same family) have been the ONLY continuous-sizing dials to clear
crypto MDD this cron trigger, while the momentum/oscillator family
(EFI/EMV/STC/Qstick/PPO) has failed crypto 5-for-5. This iteration tests
whether ER, as another member of the trend-efficiency family, also
generalizes to crypto.

Repo has 11 prior Efficiency Ratio entries but none as a continuous sizing
dial (mostly crossover/trend-strength-gate/pairs-trading constructions).
This iteration uses ER directly as a CONTINUOUS SIZING dial (already
bounded [0,1], no z-score/tanh needed -- just rescale to [0,1] exposure
multiplier) within an SMA(trend_window) uptrend gate.

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


def _efficiency_ratio(close: pd.Series, window: int) -> pd.Series:
    """Kaufman Efficiency Ratio: |NetChange(N)| / Volatility(N), bounded
    [0, 1]."""
    net_change = (close - close.shift(window)).abs()
    volatility = close.diff().abs().rolling(window).sum().replace(0, np.nan)
    er = net_change / volatility
    return er.clip(lower=0.0, upper=1.0)


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
    er_window: int = 10,
    base_exposure: float = 0.3,
    er_sensitivity: float = 0.7,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover. Since ER is
    already bounded [0, 1] and unsigned (an efficiency/strength dial, not
    a directional dial), exposure = base + sensitivity * ER, clipped, only
    applied within the SMA uptrend gate."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    er = _efficiency_ratio(close, window=er_window)

    raw_exposure = base_exposure + er_sensitivity * er
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    er_window: int = 10,
    base_exposure: float = 0.3,
    er_sensitivity: float = 0.7,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        er_window=er_window,
        base_exposure=base_exposure,
        er_sensitivity=er_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
