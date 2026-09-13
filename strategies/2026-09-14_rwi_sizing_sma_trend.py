"""Strategy: SMA(trend_window) directional gate with continuous Random Walk
Index (RWI) diff sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-104):
Random Walk Index (Michael Poulos; formula per DuckDuckGo HTML SERP results
from linnsoft.com, strike.money, stockmaniacs.net, tradingsim.com -- all
consistent): RWI_high = (High - Low[n bars ago]) / (ATR(n) * sqrt(n)),
RWI_low = (High[n bars ago] - Low) / (ATR(n) * sqrt(n)) -- compares actual
price displacement against what a pure random walk with the same ATR would
be expected to produce over n bars, so values well above 1 indicate a
statistically meaningful (non-random) directional move. Unlike VHF/PFE
(natively bounded ratios), RWI is NOT bounded to a fixed range by
construction (it can exceed 1 or even 2-3 during strong trends). This
iteration uses the SIGNED DIFFERENCE rwi_diff = RWI_high - RWI_low
(analogous to how DMI-diff turned +DI/-DI into a signed sizing dial,
2026-09-13-093) and squashes it with tanh to get a clean bounded [-1, 1]
sizing signal, rather than requiring a hand-tuned unbounded threshold.

This repo has one prior RWI entry (2026-09-04-153), a binary
threshold-crossover ENTRY trigger, decisively rejected (grid pass_fraction
10.4%, low-vol-only edge). This iteration instead uses tanh(rwi_diff) as a
CONTINUOUS SIZING dial within an SMA(trend_window) uptrend gate, testing
whether RWI's core "trend vs random walk" comparison carries more signal
once freed from an unbounded, hand-tuned threshold.

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


def _true_range(df: pd.DataFrame) -> pd.Series:
    high = df["high"]
    low = df["low"]
    prior_close = df["close"].shift(1)
    return pd.concat(
        [high - low, (high - prior_close).abs(), (low - prior_close).abs()],
        axis=1,
    ).max(axis=1)


def _rwi_diff(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """tanh(RWI_high - RWI_low), squashed to bounded [-1, 1]."""
    high = df["high"]
    low = df["low"]

    tr = _true_range(df)
    atr = tr.rolling(window).mean()
    denom = (atr * np.sqrt(window)).replace(0, np.nan)

    rwi_high = (high - low.shift(window)) / denom
    rwi_low = (high.shift(window) - low) / denom

    rwi_diff = rwi_high - rwi_low
    return np.tanh(rwi_diff)


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
    rwi_window: int = 14,
    base_exposure: float = 0.5,
    rwi_sensitivity: float = 0.65,
    leverage_cap: float = 1.0,
    deadband: float = 0.25,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    rwi_signal = _rwi_diff(df, window=rwi_window)  # already tanh-squashed to [-1, 1]

    raw_exposure = base_exposure + rwi_sensitivity * rwi_signal
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    rwi_window: int = 14,
    base_exposure: float = 0.5,
    rwi_sensitivity: float = 0.65,
    leverage_cap: float = 1.0,
    deadband: float = 0.25,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        rwi_window=rwi_window,
        base_exposure=base_exposure,
        rwi_sensitivity=rwi_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
