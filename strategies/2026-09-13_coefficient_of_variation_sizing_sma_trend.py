"""Strategy: SMA200 trend-following gate with rolling Coefficient of
Variation (CV) inverse-sizing overlay.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per https://alphax.trading/dictionary/coefficient-of-variation (browser_exec;
web_extract backend cannot fetch, only search), Coefficient of Variation
CV = std(returns) / mean(returns) -- a normalized "risk per unit of return"
measure, dimensionless, where LOWER CV means a more efficient (less noisy)
return stream and HIGHER CV means the return stream is dominated by noise
relative to its own average trend. This is structurally distinct from every
Sharpe-family ratio already tested in this repo (Sharpe/Sortino/Omega/UPI/
Rachev/Tail/Burke/Pain/Sterling/Treynor/Kappa/Cornish-Fisher-Sharpe): those
all put an EXCESS-RETURN numerator over a risk denominator (higher=better,
scale exposure UP with the ratio). CV inverts the fraction (std/mean, not
mean/std) and omits any risk-free/target subtraction -- so this iteration
scales exposure INVERSELY with trailing CV (exposure = clip(cv_reference /
trailing_cv, 0, leverage_cap)): the lower the noise-to-trend ratio, the
higher the exposure. First Coefficient-of-Variation-based sizing overlay in
this repo.

Signal logic
------------
- Base directional signal: long when close > SMA(trend_window), flat
  otherwise (identical trend gate to the repo's other sizing-overlay
  strategies for direct comparability).
- Within each trailing `cv_window`, compute mean daily log return and its
  standard deviation; CV = std / abs(mean) (guarded against near-zero mean).
- Exposure: scale = clip(cv_reference / (CV + adjustment), 0, leverage_cap).
  Applied only while the trend gate is long.

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


def _rolling_cv(close: pd.Series, window: int, adjustment: float) -> pd.Series:
    """Rolling Coefficient of Variation: std(returns) / abs(mean(returns))."""
    log_ret = np.log(close / close.shift(1))
    values = log_ret.to_numpy(dtype=float)
    n = len(values)
    out = np.full(n, np.nan)
    if n < window:
        return pd.Series(out, index=close.index)

    for end in range(window - 1, n):
        start = end - window + 1
        seg = values[start:end + 1]
        seg = seg[~np.isnan(seg)]
        if len(seg) < 10:
            continue
        mean_ret = float(np.mean(seg))
        std_ret = float(np.std(seg))
        denom = abs(mean_ret) + adjustment
        if denom <= 1e-10:
            continue
        out[end] = std_ret / denom

    return pd.Series(out, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    cv_window: int = 60,
    adjustment: float = 1e-4,
    cv_reference: float = 5.0,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    cv = _rolling_cv(close, cv_window, adjustment)

    raw_exposure = (cv_reference / cv.replace(0, np.nan)).astype(float)
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
