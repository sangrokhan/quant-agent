"""Strategy: Inverse-EWMA(RiskMetrics)-volatility position-sizing overlay on
a plain SMA trend signal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-058):
Per RiskMetrics (J.P. Morgan)'s standard methodology (confirmed via
riskhub.org/ryanoconnellfinance.com/learnsignal.com Google SERP
snippets), the Exponentially Weighted Moving Average (EWMA) volatility
estimator uses a decay factor lambda=0.94 for daily data:

    sigma_t^2 = lambda * sigma_{t-1}^2 + (1 - lambda) * r_{t-1}^2

where r is the daily log return. Unlike a simple rolling-window
close-to-close std (already tested in this repo as the baseline
inverse-vol-targeting overlay, 2026-09-08-165) or the OHLC range-based
estimators already swapped in this trigger (Parkinson 2026-09-17-050/051,
Garman-Klass 2026-09-17-052, Rogers-Satchell 2026-09-17-053), EWMA gives
exponentially decaying weight to ALL historical returns rather than a
hard cutoff at a fixed lookback window -- so a volatility spike is
picked up faster (heavier weight on yesterday's shock) but also decays
back down smoothly rather than dropping out abruptly once it exits a
fixed rolling window. This is a genuinely distinct estimator (0 prior KB
hits on "EWMA"/"RiskMetrics"/"exponentially weighted moving average"),
completing a 5th vol-estimator-swap variant on the identical SMA-trend-
gate + deadband sizing-dial construction validated for the other four
this trigger.

Signal logic
------------
- Trend gate: close > SMA(trend_window) -> want to be long, else flat.
- When long, size the position as
  exposure = min(target_vol / ewma_vol, leverage_cap), using ONLY
  trailing (non-look-ahead) EWMA volatility (annualized), seeded from the
  first `warmup_window` daily log-return variance.
- Rebalance-buffer deadband: hold exposure constant unless the new target
  differs from the last held value by more than `deadband`.
- Both the trend gate and EWMA vol estimate use data available strictly
  before the trading day (exposure shifted by 1 bar in generate_returns).

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


def _ewma_vol(close: pd.Series, lam: float, warmup_window: int) -> pd.Series:
    """Rolling annualized RiskMetrics-style EWMA volatility.

    sigma_t^2 = lam * sigma_{t-1}^2 + (1-lam) * r_{t-1}^2, seeded with the
    simple variance of the first `warmup_window` log returns.
    """
    safe_close = close.where(close > 0)
    log_ret = np.log(safe_close / safe_close.shift(1))

    values = log_ret.to_numpy()
    n = len(values)
    var = np.full(n, np.nan)

    # Seed at the first index where we have warmup_window returns available.
    seed_idx = None
    for i in range(n):
        if i >= warmup_window:
            window = values[i - warmup_window:i]
            if not np.isnan(window).any():
                var[i] = np.nanvar(window)
                seed_idx = i
                break
    if seed_idx is None:
        return pd.Series(np.nan, index=close.index)

    for i in range(seed_idx + 1, n):
        prev_ret = values[i - 1]
        prev_ret_sq = prev_ret ** 2 if not np.isnan(prev_ret) else 0.0
        var[i] = lam * var[i - 1] + (1 - lam) * prev_ret_sq

    ewma_variance = pd.Series(var, index=close.index)
    return np.sqrt(ewma_variance.clip(lower=0.0)) * np.sqrt(252.0)


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
    trend_window: int = 200,
    lam: float = 0.94,
    warmup_window: int = 20,
    target_vol: float = 0.15,
    leverage_cap: float = 1.5,
    deadband: float = 0.15,
) -> pd.Series:
    """Return a continuous target-exposure series in [0, leverage_cap],
    deadband-held to control turnover."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    trend_long = close > sma

    ewma_vol = _ewma_vol(close, lam, warmup_window)
    safe_vol = ewma_vol.clip(lower=1e-4)
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
