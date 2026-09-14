"""Strategy: SMA(trend_window) directional gate with continuous Ehlers
Fisher Transform sizing overlay + deadband, leverage-cap-aware for
crypto from the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger,
10th and final iteration): John Ehlers' Fisher Transform (formula per this
repo's own prior entries 2026-09-04-051 and 10+ others, no new fetch
needed this iteration): price is rescaled to [-1, 1] within its own
rolling high/low range (value1), then passed through the Fisher Transform
formula Fisher = 0.5 * ln((1+value1)/(1-value1)), smoothed. The transform
statistically normalizes price toward a Gaussian distribution, sharpening
turning points into distinct, naturally-bounded (~[-3, 3] in practice)
peaks -- explicitly well-suited to graded/continuous interpretation, not
just a binary threshold/crossover.

This repo has 13+ prior Fisher Transform entries (2026-09-04-051 and many
variants: RVI-of-Fisher, Fisher-on-RSI, Inverse Fisher on Stochastic/RSI,
slope-reversal, etc.), ALL using Fisher (or its inverse) as a BINARY
threshold-crossover/slope-reversal ENTRY construction, ALL rejected. This
is the FIRST iteration to reframe the plain price Fisher Transform itself
as a CONTINUOUS SIZING dial, applying this cron trigger's leverage-cap-
aware crypto methodology (2026-09-14-124 through 129) from the start.

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


def _fisher_transform(close: pd.Series, window: int = 10, smooth_alpha: float = 0.33) -> pd.Series:
    """Ehlers Fisher Transform.

    value1[t] = 0.66 * ((price[t] - lo)/(hi - lo) * 2 - 1) + 0.67*value1[t-1]
    (standard Ehlers exponential smoothing of the rescaled price), clipped
    to (-0.999, 0.999) to avoid log(0)/infinite Fisher values;
    Fisher[t] = 0.5*ln((1+value1[t])/(1-value1[t])) + 0.5*Fisher[t-1]
    -- Ehlers' own double-smoothed construction, naturally bounded
    roughly [-3, 3] in typical market conditions (unbounded in the limit
    but practically well-behaved with the smoothing terms).
    """
    hi = close.rolling(window).max()
    lo = close.rolling(window).min()
    rng = (hi - lo).replace(0, np.nan)
    raw = ((close - lo) / rng * 2.0 - 1.0).fillna(0.0)

    value1 = np.zeros(len(close))
    fisher = np.zeros(len(close))
    raw_arr = raw.to_numpy()
    for i in range(1, len(close)):
        v = smooth_alpha * raw_arr[i] + (1 - smooth_alpha) * value1[i - 1]
        v = min(max(v, -0.999), 0.999)
        value1[i] = v
        fisher[i] = 0.5 * np.log((1 + v) / (1 - v)) + 0.5 * fisher[i - 1]

    return pd.Series(fisher, index=close.index)


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
    fisher_window: int = 10,
    fisher_reference: float = 1.5,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    fisher = _fisher_transform(close, window=fisher_window)
    fisher_norm = (fisher / fisher_reference).clip(lower=-1.5, upper=1.5)

    raw_exposure = base_exposure + sensitivity * fisher_norm
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    fisher_window: int = 10,
    fisher_reference: float = 1.5,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        fisher_window=fisher_window,
        fisher_reference=fisher_reference,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
