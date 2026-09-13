"""Strategy: SMA200 trend-following gate with rolling Gain-to-Pain-Ratio
(Schwager) dynamic exposure scaling.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per Jack Schwager's Gain-to-Pain Ratio (GPR, popularized in Market
Wizards; formula confirmed via Google AI Overview / TradesViz /
WallStreetMojo, read via browser_exec this iteration after web_search
returned zero results for the direct query): GPR = sum(all periodic
returns, gains AND losses) / abs(sum(negative periodic returns only)).
Interpretation bands per source: <1.0 poor, 1.0-1.5 good, 1.5-2.0+
excellent, 3.0-4.0+ world-class consistency (Peter Brandt). Unlike Sharpe,
GPR applies NO penalty for upside volatility -- it purely tracks
cumulative "pain" (loss magnitude) relative to total net return.

This strategy scales an SMA(200) trend gate's exposure by the underlying
asset's own trailing GPR, hypothesizing that GPR's distinct arithmetic
(SUM-based, not mean-based like Omega, and using ALL returns in the
numerator rather than only the gains) captures a different aspect of
"smoothness of the equity curve" than any of this repo's other sizing
overlays tested this cron trigger (inverse-vol, CVaR, MAR-ratio,
downside-deviation, Omega-ratio). First Gain-to-Pain-Ratio-based strategy
in this repo.

Signal logic
------------
- Base directional signal: long when close > SMA(trend_window), flat
  otherwise (identical trend gate to the repo's other sizing-overlay
  strategies, isolating the sizing-mechanism variable).
- Rolling GPR over `gpr_window` days of daily returns: GPR = sum(all
  returns in window) / abs(sum(negative returns in window)).
- Exposure: scale = clip(gpr / gpr_reference, 0, leverage_cap), where
  gpr_reference is a normalizing constant (GPR level mapping to full 1.0x
  exposure; per source's "good" band starting at 1.0, gpr_reference
  defaults to 1.0).

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


def _rolling_gain_to_pain_ratio(daily_ret: pd.Series, window: int) -> pd.Series:
    """Rolling Gain-to-Pain Ratio (Schwager): sum of all periodic returns
    divided by the absolute value of the sum of negative periodic returns
    only. Vectorized via numpy sliding windows."""
    values = daily_ret.to_numpy(dtype=float)
    n = len(values)
    out = np.full(n, np.nan)
    if n < window:
        return pd.Series(out, index=daily_ret.index)

    windows = np.lib.stride_tricks.sliding_window_view(values, window)
    total_ret = np.nansum(windows, axis=1)
    negative_only = np.minimum(windows, 0.0)
    pain = np.abs(np.nansum(negative_only, axis=1))
    with np.errstate(divide="ignore", invalid="ignore"):
        gpr = np.where(pain > 1e-12, total_ret / pain, np.nan)

    out[window - 1:] = gpr
    return pd.Series(out, index=daily_ret.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    gpr_window: int = 60,
    gpr_reference: float = 1.0,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    daily_ret = close.pct_change()
    gpr = _rolling_gain_to_pain_ratio(daily_ret, gpr_window)

    raw_exposure = (gpr / gpr_reference).astype(float)
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
