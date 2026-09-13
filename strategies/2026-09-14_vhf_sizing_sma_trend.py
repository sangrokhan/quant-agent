"""Strategy: SMA(trend_window) directional gate with continuous Vertical
Horizontal Filter (VHF) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-101):
Vertical Horizontal Filter (Adam White; formula per DuckDuckGo HTML SERP
results from ta-lib.org, gocharting.com, technicalresources.in,
trendspider.com -- all consistent): VHF = (highest_close - lowest_close) /
sum(|close.diff()|) over a rolling window -- the net directional range a
window covered divided by the total path length actually traveled.
Naturally bounded [0, 1] by construction (net displacement can never exceed
cumulative absolute path length). Values near 1 mean price moved mostly in
one direction (efficient/trending); values near 0 mean price retraced
repeatedly and went nowhere (choppy/ranging). VHF measures trend STRENGTH
(unsigned), analogous in role to ADX/CHOP which were both successfully
turned into continuous sizing dials earlier this cron trigger.

This repo has 2 prior VHF entries, both binary trend-efficiency GATE
constructions (require VHF above/rising past a threshold to permit trading),
both rejected. Neither used VHF as a CONTINUOUS SIZING dial. This iteration
applies the same reframing that rescued ADX/CHOP (both also unsigned
trend-strength measures) earlier this cron trigger: within an
SMA(trend_window) uptrend gate, exposure scales continuously with VHF level
(higher VHF = more efficient/trending market = larger position) rather than
requiring VHF to clear a hard threshold before any exposure is taken.

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


def _vhf(close: pd.Series, window: int = 28) -> pd.Series:
    """VHF = (highest_close - lowest_close) / sum(|close.diff()|), bounded
    [0, 1] by construction (net displacement <= cumulative path length)."""
    hh = close.rolling(window).max()
    ll = close.rolling(window).min()
    net_range = hh - ll

    path_length = close.diff().abs().rolling(window).sum()

    vhf = net_range / path_length.replace(0, np.nan)
    return vhf.clip(lower=0.0, upper=1.0)


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
    vhf_window: int = 28,
    base_exposure: float = 0.5,
    vhf_sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.25,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    vhf = _vhf(close, window=vhf_window)  # already in [0, 1]
    # rescale [0,1] -> [-1,1] around a 0.5 "neutral efficiency" midpoint so
    # low-VHF (choppy) periods pull exposure DOWN below base_exposure, and
    # high-VHF (trending) periods push it UP, matching the CHOP/ADX pattern.
    vhf_norm = (vhf - 0.5) * 2.0

    raw_exposure = base_exposure + vhf_sensitivity * vhf_norm
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    vhf_window: int = 28,
    base_exposure: float = 0.5,
    vhf_sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.25,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        vhf_window=vhf_window,
        base_exposure=base_exposure,
        vhf_sensitivity=vhf_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
