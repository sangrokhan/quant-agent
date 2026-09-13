"""Strategy: multi-horizon Donchian-channel breakout ENSEMBLE combined with
volatility-targeting position sizing.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-115):
Source: https://www.quantifiedstrategies.com/crypto-trend-trading-strategy/
(summarizing Zarattini, Pagani & Barbon, "Catching Crypto Trends: A Tactical
Approach for Bitcoin and Altcoins"). The paper's mechanism: instead of a
single-lookback Donchian breakout (long when close > N-day high), aggregate
breakout signals from MANY lookback horizons simultaneously (e.g. 5, 10, 20,
30, 60, 90, 150, 250, 360 days) into one ensemble exposure signal (fraction
of horizons currently "long"), then size the position via volatility
targeting (target_annual_vol / realized_vol, capped at leverage_cap) rather
than a binary 0/1 position.

This repo has ~15 prior single-window Donchian breakout entries (see
strategies_index.jsonl grep "donchian"), essentially all of which failed
crypto decisively on max-drawdown (typically 0/54 grid cells). This
iteration is NOT another single-window breakout variant with a new
filter/exit — it tests the paper's specific claim that a MULTI-HORIZON
ENSEMBLE (diversifying across many lookback windows at once, reducing
whipsaw sensitivity to any single window choice) combined with vol
targeting is what let the paper report BTC max drawdown of 19% vs 80%+ for
buy-and-hold. This is the "structurally different crypto approach" flagged
in this repo's own meta-finding after 10/10 continuous-sizing-dial variants
failed on crypto MDD last cron trigger.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

DEFAULT_WINDOWS: Sequence[int] = (5, 10, 20, 30, 60, 90, 150, 250)


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _ensemble_donchian_fraction(close: pd.Series, windows: Sequence[int]) -> pd.Series:
    """Fraction of lookback windows currently in a breakout-long state.

    For each window N: long (1) if close > rolling N-day high as of the
    PRIOR bar (i.e. today's close breaks yesterday's N-day high-water mark),
    flat (0) if close < rolling N-day low as of the prior bar, otherwise
    hold the previous state for that window (classic Donchian
    channel/turtle logic per-window), then average across all windows.
    """
    n = len(close)
    frac = pd.Series(0.0, index=close.index)
    per_window_states = []
    for w in windows:
        upper = close.rolling(w).max().shift(1)
        lower = close.rolling(w).min().shift(1)
        state = np.zeros(n)
        cur = 0.0
        c = close.to_numpy()
        u = upper.to_numpy()
        l = lower.to_numpy()
        for i in range(n):
            if not np.isnan(u[i]) and c[i] > u[i]:
                cur = 1.0
            elif not np.isnan(l[i]) and c[i] < l[i]:
                cur = 0.0
            state[i] = cur
        per_window_states.append(state)
    frac = pd.Series(np.mean(per_window_states, axis=0), index=close.index)
    return frac


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    """Hold the last rebalanced exposure until it drifts by more than
    `deadband`, following this repo's established rebalance-buffer pattern
    for cutting turnover on daily-recomputed continuous sizing signals."""
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
    donchian_windows: Sequence[int] = DEFAULT_WINDOWS,
    target_annual_vol: float = 0.20,
    vol_lookback: int = 20,
    leverage_cap: float = 1.0,
    min_vol_floor: float = 0.01,
    deadband: float = 0.1,
) -> pd.Series:
    """Return continuous [0, leverage_cap] exposure: ensemble Donchian
    breakout fraction (directional signal) scaled by inverse realized
    volatility targeting (risk sizing), matching the paper's two-stage
    "signal, then size" construction. A deadband/rebalance-buffer holds the
    exposure constant until it drifts materially, cutting daily turnover
    (this repo's established fix pattern for continuous-sizing strategies).
    """
    df = _prep(price_df)
    close = df["close"]

    breakout_fraction = _ensemble_donchian_fraction(close, donchian_windows)

    daily_ret = close.pct_change()
    realized_vol = daily_ret.rolling(vol_lookback).std() * np.sqrt(252)
    realized_vol = realized_vol.clip(lower=min_vol_floor)

    vol_scalar = (target_annual_vol / realized_vol).clip(upper=leverage_cap)
    vol_scalar = vol_scalar.fillna(0.0)

    raw_exposure = (breakout_fraction * vol_scalar).clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.fillna(0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    donchian_windows: Sequence[int] = DEFAULT_WINDOWS,
    target_annual_vol: float = 0.20,
    vol_lookback: int = 20,
    leverage_cap: float = 1.0,
    min_vol_floor: float = 0.01,
    deadband: float = 0.1,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        donchian_windows=donchian_windows,
        target_annual_vol=target_annual_vol,
        vol_lookback=vol_lookback,
        leverage_cap=leverage_cap,
        min_vol_floor=min_vol_floor,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
