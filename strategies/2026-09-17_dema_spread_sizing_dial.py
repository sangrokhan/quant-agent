"""Strategy: DEMA fast-minus-slow spread (normalized by slow DEMA) as a
CONTINUOUS SIZING dial on the DEMA crossover's own directional gate,
leverage-cap-aware for crypto.

Hypothesis (this cron trigger's iteration 8, direct fix attempt for
2026-09-17-076's crypto rejection):
2026-09-17-076 tested DEMA (Patrick Mulloy 1994, formula/source already
confirmed this cron trigger, not re-fetched) fast/slow crossover as a
binary long/flat trigger: accepted on equity (per-symbol tuned configs)
but decisively rejected on crypto (BTC/USDT MDD 0.458, ETH/USDT MDD 0.551,
both ~2x the 0.25 cap) due to full binary exposure with no vol-scaling.
This iteration reframes the same DEMA fast/slow relationship as a
CONTINUOUS SIZING dial: the normalized spread (fast_dema-slow_dema)/
slow_dema is rolling z-scored and tanh-squashed to [-1,1], used as an
exposure multiplier (rather than a full 0/1 flip), leverage-cap-aware for
crypto from the start -- this repo's standard rescue pattern for
binary-trigger crypto MDD failures (already validated for MAD,
NVI, PVO, and this same cron trigger's WaveTrend).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap])
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _dema(close: pd.Series, span: int) -> pd.Series:
    ema1 = close.ewm(span=span, adjust=False).mean()
    ema2 = ema1.ewm(span=span, adjust=False).mean()
    return 2 * ema1 - ema2


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
    fast_period: int = 20,
    slow_period: int = 50,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Normalized DEMA fast-minus-slow spread is rolling z-scored and
    tanh-squashed to [-1,1], used as a sizing dial (long-only: dial rises
    with bullish fast-over-slow spread, exposure floored at 0).
    """
    df = _prep(price_df)
    close = df["close"]

    fast_dema = _dema(close, fast_period)
    slow_dema = _dema(close, slow_period)
    spread = (fast_dema - slow_dema) / slow_dema.replace(0.0, np.nan)

    roll_mean = spread.rolling(zscore_window).mean()
    roll_std = spread.rolling(zscore_window).std().replace(0.0, np.nan)
    z = (spread - roll_mean) / roll_std
    dial = np.tanh(z.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    fast_period: int = 20,
    slow_period: int = 50,
    zscore_window: int = 100,
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
        fast_period=fast_period,
        slow_period=slow_period,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
