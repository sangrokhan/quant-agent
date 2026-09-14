"""Strategy: SMA(trend_window) directional gate with continuous Ehlers
Center of Gravity (CG) oscillator sizing overlay + deadband, applying
this cron trigger's leverage-cap-aware crypto sizing from the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
John Ehlers' Center of Gravity oscillator (Cybernetic Analysis, 2004;
formula per https://www.quantum-algo.com/blog/guides/center-of-gravity-indicator-complete-guide/
and this repo's own prior entries 2026-09-04-124/2026-09-10-060, both
already read this cron trigger, browser_exec-confirmed no new content
this iteration -- formula unchanged): CG_t = -sum((i+1)*Price[t-i]) /
sum(Price[t-i]) over a lookback window i=0..n-1 -- a near-zero-lag
"balance point" oscillator. Not natively hard-bounded like RSI/CCI/CMO,
but naturally oscillates in a roughly stable range proportional to the
lookback window (roughly -window/2 to 0 by construction), so this
iteration normalizes it by its own rolling range (min-max over a longer
window) into [-1, 1] before use as a sizing dial.

This repo has 2 prior CG entries (2026-09-04-124 ADX-gated signal-line
crossover, 2026-09-10-060 signal-line crossover), both binary ENTRY
triggers, both rejected. This iteration is the first to reframe CG as a
CONTINUOUS SIZING dial, and -- per this cron trigger's leverage-cap lesson
(2026-09-14-124/125/126) -- is grid-tested with crypto pre-capped at a
lower leverage_cap from the start.

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


def _center_of_gravity(close: pd.Series, window: int) -> pd.Series:
    """CG_t = -sum((i+1)*Price[t-i]) / sum(Price[t-i]), i=0..window-1.

    Ehlers' balance-point oscillator; near-zero-lag turning-point
    indicator. Not natively hard-bounded, so this function returns the
    raw value and normalization happens in the caller.
    """
    weights = np.arange(1, window + 1)

    def _cg(vals: np.ndarray) -> float:
        num = np.sum(weights * vals[::-1])
        denom = np.sum(vals)
        if denom == 0:
            return np.nan
        return -num / denom

    return close.rolling(window).apply(_cg, raw=True)


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
    cg_window: int = 10,
    norm_window: int = 120,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    cg = _center_of_gravity(close, window=cg_window)
    cg_min = cg.rolling(norm_window).min()
    cg_max = cg.rolling(norm_window).max()
    cg_range = (cg_max - cg_min).replace(0, np.nan)
    cg_norm = (2.0 * (cg - cg_min) / cg_range - 1.0).clip(lower=-1.0, upper=1.0)

    raw_exposure = base_exposure + sensitivity * cg_norm
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    cg_window: int = 10,
    norm_window: int = 120,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        cg_window=cg_window,
        norm_window=norm_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
