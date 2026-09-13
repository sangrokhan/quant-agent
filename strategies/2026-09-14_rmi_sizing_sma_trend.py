"""Strategy: SMA(trend_window) directional gate with continuous Relative
Momentum Index (RMI) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-097):
Relative Momentum Index (Roger Altman, 1993, Technical Analysis of Stocks &
Commodities; formula per DuckDuckGo HTML SERP results from everycalculators.com,
luxalgo.com/library/concept/relative-momentum-index, onetradejournal.com,
quantstrategy.io, all consistent): RMI is Wilder's RSI construction applied
to an N-bar momentum step (close vs close `momentum_period` bars back)
instead of the standard 1-bar diff, then smoothed and rescaled to [0,100]
exactly like RSI: RMI = 100 - 100/(1 + RS), RS = smoothed-avg-up-momentum /
smoothed-avg-down-momentum over `momentum_period`-bar changes.

This repo has one prior RMI entry (2026-09-05-013), a binary
oversold-threshold mean-reversion ENTRY trigger, rejected for insufficient
trade count (QQQ nominal pass on only 5 trades). This iteration instead uses
RMI as a CONTINUOUS SIZING dial (rescaled to [-1,1] around its 50-midpoint)
within an SMA(trend_window) uptrend gate, following the same reframing
pattern that rescued VZO/ADX/DMI-diff/CHOP/Vortex-diff-ratio/TSI earlier
this cron trigger (all previously binary-triggered and rejected, all
accepted once reframed as continuous position-sizing dials rather than
discrete entry/exit signals) -- directly testing whether RMI's earlier
low-trade-count rejection was a symptom of the binary-threshold
construction rather than RMI itself lacking signal.

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


def _rmi(close: pd.Series, momentum_period: int = 5, smoothing_period: int = 14) -> pd.Series:
    """RMI = 100 - 100/(1+RS), RS computed on `momentum_period`-bar momentum
    with Wilder-style (EMA alpha=1/smoothing_period) smoothing, bounded
    [0, 100] like RSI."""
    mom = close.diff(momentum_period)
    up = mom.clip(lower=0.0)
    down = (-mom).clip(lower=0.0)

    alpha = 1.0 / smoothing_period
    avg_up = up.ewm(alpha=alpha, adjust=False).mean()
    avg_down = down.ewm(alpha=alpha, adjust=False).mean()

    rs = avg_up / avg_down.replace(0, np.nan)
    rmi = 100.0 - (100.0 / (1.0 + rs))
    return rmi.clip(lower=0.0, upper=100.0)


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
    momentum_period: int = 5,
    smoothing_period: int = 14,
    base_exposure: float = 0.5,
    rmi_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    rmi = _rmi(close, momentum_period=momentum_period, smoothing_period=smoothing_period)
    rmi_norm = (rmi - 50.0) / 50.0  # rescale to roughly [-1, 1] around midpoint

    raw_exposure = base_exposure + rmi_sensitivity * rmi_norm
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    momentum_period: int = 5,
    smoothing_period: int = 14,
    base_exposure: float = 0.5,
    rmi_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        momentum_period=momentum_period,
        smoothing_period=smoothing_period,
        base_exposure=base_exposure,
        rmi_sensitivity=rmi_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
