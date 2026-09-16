"""Strategy: Parkinson-vol inverse-vol-targeting overlay + rebalance-buffer
deadband to control turnover (crypto rescue follow-up).

Hypothesis (knowledge_base id TBD, this cron trigger, 2nd iteration):
Direct follow-up to this same cron trigger's prior iteration (id
2026-09-17-050, strategies/2026-09-17_parkinson_vol_targeting_trend_overlay.py):
the plain Parkinson-vol inverse-vol-targeting overlay passed MORE grid
cells for crypto than equity on a raw Sharpe/MDD basis (57% vs 47% pass
fraction), but was rejected for crypto specifically because the
single-config validator run failed transaction-cost survival -- the daily-
updating continuous sizing dial produced ~1400-1500 "trades" (exposure
changes) over the sample, and even a modest 5bps/trade cost assumption wiped
out the edge (net Sharpe 0.16-0.26 vs the 0.5 threshold). This iteration
adds a rebalance-buffer DEADBAND (only re-size when the new target exposure
differs from the currently-held exposure by more than `deadband`) on top of
the identical, unchanged Parkinson-vol/SMA-trend construction, following
this repo's own established deadband precedent for controlling turnover on
continuous sizing dials (e.g. 2026-09-14-115's Donchian-ensemble
vol-targeting overlay used deadband=0.15 to control crypto turnover; the
Amihud/Corwin-Schultz continuous-sizing-dial strategies at
2026-09-16-139/140 also use a deadband for the same reason). No new
external source needed this sub-iteration -- same source material as
2026-09-17-050 (ryanoconnellfinance.com, quantra.quantinsti.com Parkinson
estimator explainers).

Signal logic
------------
- Identical trend gate + Parkinson-vol inverse-vol-targeting raw exposure
  computation as the predecessor strategy.
- NEW: hold the exposure constant unless the newly-computed target exposure
  differs from the last HELD value by more than `deadband` (absolute
  units of the [0, leverage_cap] exposure scale) -- this is a stateful,
  sequential rule (cannot be vectorized without a loop) so it's applied via
  an explicit Python loop over the raw exposure series, matching the same
  pattern already used by this repo's other deadband-smoothed continuous
  sizing dials (see strategies/2026-09-16_amihud_illiq_sizing_sma_trend.py's
  `_apply_deadband` helper, which this file reuses verbatim).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap], deadband-held between rebalances).
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


def _parkinson_vol(high: pd.Series, low: pd.Series, vol_window: int) -> pd.Series:
    """Rolling annualized Parkinson (1980) high-low range volatility."""
    safe_high = high.where(high > 0)
    safe_low = low.where(low > 0)
    log_hl = np.log(safe_high / safe_low)
    per_bar_var = (log_hl ** 2) / (4.0 * np.log(2.0))
    rolling_var = per_bar_var.rolling(vol_window, min_periods=vol_window).mean()
    return np.sqrt(rolling_var) * np.sqrt(252.0)


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    """Hold exposure constant unless the new target differs from the last
    HELD value by more than `deadband` (absolute units)."""
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
    trend_window: int = 200,
    vol_window: int = 20,
    target_vol: float = 0.15,
    leverage_cap: float = 1.5,
    deadband: float = 0.15,
) -> pd.Series:
    """Return a continuous target-exposure series in [0, leverage_cap],
    held constant within `deadband` of the last rebalance to cut turnover."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    sma = close.rolling(trend_window).mean()
    trend_long = close > sma

    parkinson_vol = _parkinson_vol(high, low, vol_window)
    safe_vol = parkinson_vol.clip(lower=1e-4)
    raw_exposure = (target_vol / safe_vol).clip(upper=leverage_cap)

    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)
    raw_exposure = raw_exposure.fillna(0.0).clip(lower=0.0, upper=leverage_cap)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
