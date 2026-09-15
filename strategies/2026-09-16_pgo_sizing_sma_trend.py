"""Strategy: SMA(trend_window) directional gate with continuous PGO
(Pretty Good Oscillator, Mark Johnson) sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
PGO (Pretty Good Oscillator, Mark Johnson) measures price's distance
from its own moving average in ATR units:

    PGO = (Close - SMA(Close, N)) / EMA(TrueRange, N)

Repo has 2 prior PGO entries, both binary breakout-threshold triggers
(PGO crossing above +3.0, exit on zero-line reversion): 2026-09-08-049
(near-miss, QQQ Sharpe 0.998/MDD 0.252 breach) and its follow-up
2026-09-09-052 (added SMA(200) trend gate + ATR trailing stop, still
rejected). Neither prior attempt used PGO as a continuous sizing dial.
Formula already confirmed in this repo from the prior entries (per
pineify.app, no new fetch needed this sub-iteration -- formula not in
question, only the sizing reframing is new).

This iteration reframes PGO as a CONTINUOUS SIZING dial (rolling z-score
normalized + tanh-squashed to [-1,1], since raw PGO is ATR-normalized but
not bounded to a fixed range) rather than a fixed +3.0 breakout threshold,
inside an SMA(trend_window) uptrend gate with a deadband to cut turnover,
following this repo's established continuous-sizing-dial pattern,
leverage-cap-aware for crypto from the start. First PGO continuous-sizing
variant in this repo.

Source: https://pineify.app (formula already documented in this repo from
prior entry 2026-09-08-049, reused unchanged, no new fetch this
sub-iteration).

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
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _compute_pgo(df: pd.DataFrame, window: int) -> pd.Series:
    close = df["close"]
    sma = close.rolling(window).mean()
    tr = _true_range(df)
    atr = tr.ewm(span=window, adjust=False).mean().replace(0.0, np.nan)
    pgo = (close - sma) / atr
    return pgo


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
    pgo_window: int = 21,
    zscore_window: int = 60,
    base_exposure: float = 0.4,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    PGO is rolling z-score normalized then tanh-squashed to bounded
    [-1,1], used as a sizing dial gated by an SMA(trend_window) uptrend
    filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    pgo = _compute_pgo(df, pgo_window)
    roll_mean = pgo.rolling(zscore_window, min_periods=zscore_window).mean()
    roll_std = pgo.rolling(zscore_window, min_periods=zscore_window).std().replace(0.0, np.nan)
    z = ((pgo - roll_mean) / roll_std).fillna(0.0)
    dial = np.tanh(z)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    pgo_window: int = 21,
    zscore_window: int = 60,
    base_exposure: float = 0.4,
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
        pgo_window=pgo_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
