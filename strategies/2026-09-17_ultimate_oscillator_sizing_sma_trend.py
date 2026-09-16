"""Strategy: SMA(trend_window) trend-following gate with continuous Ultimate
Oscillator (UO, Larry Williams) sizing overlay.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-021):
This repo has 2 prior Ultimate Oscillator entries (2026-09-04-050 plain
oversold/overbought threshold-cross, rejected; 2026-09-05-077 bullish
divergence variant, rejected) -- both using UO as a BINARY entry trigger.
Neither used it as a CONTINUOUS SIZING dial, which is the successful
established pattern this cron trigger has repeatedly used to rescue
previously-binary-rejected oscillators (Vortex 2026-09-13-095 accepted,
CCI 2026-09-13-073, Chaikin Oscillator 2026-09-14-122 accepted equity,
Twiggs Money Flow 2026-09-14-123 accepted equity, DeMarker 2026-09-14-132,
etc.). UO is naturally centered around 50 with a conventional [0,100]
range (per QuantifiedStrategies.com / Investopedia's disclosed formula:
weighted 4:2:1 blend of 7/14/28-period buying-pressure-over-true-range
ratios), so this iteration rescales (UO-50)/50 to a signed [-1,1] dial and
uses it to size exposure within an SMA(trend_window) uptrend gate, rather
than trading it as a standalone crossover signal.

Signal logic
------------
- Base directional gate: long-candidate when close > SMA(trend_window).
- Ultimate Oscillator (UO) over 7/14/28-period windows, weighted 4:2:1
  (standard Larry Williams construction).
- Exposure while trend_long: clip(base_exposure + sensitivity*(UO-50)/50,
  0, leverage_cap) -- scale exposure up as UO climbs above its 50
  midpoint (accelerating buying pressure), scale down toward zero as UO
  falls back toward/below 50 even while the slower SMA trend gate is
  still nominally long.

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


def _ultimate_oscillator(
    df: pd.DataFrame, p1: int = 7, p2: int = 14, p3: int = 28
) -> pd.Series:
    close = df["close"]
    low = df["low"]
    high = df["high"]
    prior_close = close.shift(1)

    bp = close - pd.concat([low, prior_close], axis=1).min(axis=1)
    tr = pd.concat([high, prior_close], axis=1).max(axis=1) - pd.concat(
        [low, prior_close], axis=1
    ).min(axis=1)

    avg1 = bp.rolling(p1).sum() / tr.rolling(p1).sum()
    avg2 = bp.rolling(p2).sum() / tr.rolling(p2).sum()
    avg3 = bp.rolling(p3).sum() / tr.rolling(p3).sum()

    uo = 100.0 * (4.0 * avg1 + 2.0 * avg2 + 1.0 * avg3) / 7.0
    return uo


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    uo_p1: int = 7,
    uo_p2: int = 14,
    uo_p3: int = 28,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    deadband: float = 0.0,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    uo = _ultimate_oscillator(df, p1=uo_p1, p2=uo_p2, p3=uo_p3)
    uo_centered = ((uo - 50.0) / 50.0).astype(float)

    if deadband > 0:
        uo_centered = uo_centered.where(uo_centered.abs() > deadband, 0.0)

    raw_exposure = base_exposure + sensitivity * uo_centered
    exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap).fillna(0.0)

    position = exposure.where(trend_long.fillna(False), other=0.0)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
