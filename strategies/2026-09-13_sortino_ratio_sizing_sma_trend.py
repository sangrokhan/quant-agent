"""Strategy: SMA200 trend-following gate with rolling Sortino Ratio dynamic
exposure scaling.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
This repo has one prior downside-deviation-based sizing overlay
(2026-09-13-048), but that construction used a pure inverse-risk sizing
rule (exposure = target_downside_dev / rolling_downside_deviation, with NO
return term at all -- a vol-targeting-style overlay, not a risk-adjusted
performance RATIO). This iteration tests the genuine Sortino RATIO itself
(F. Sortino, popularized via https://www.investopedia.com/terms/s/sortinoratio.asp,
read via browser_exec): Sortino = (return - target) / downside_deviation,
where downside_deviation = sqrt(mean(min(0, r - target)^2)). Unlike
2026-09-13-048's sizing rule (denominator only, no numerator), this scales
exposure by the full excess-return-over-downside-risk ratio -- structurally
identical in FORM to this cron trigger's other accepted risk-ratio sizing
overlays (UPI/Kappa-3/Tail-Ratio/Rachev), but using the specific classic
Sortino denominator (semi-deviation, not RMS-drawdown/cubed-LPM/percentile/
CVaR). First genuine Sortino-RATIO-based (not just downside-deviation
inverse-sizing) sizing overlay in this repo.

Signal logic
------------
- Base directional signal: long when close > SMA(trend_window), flat
  otherwise (identical trend gate to the repo's other sizing-overlay
  strategies, for direct comparability).
- Within each trailing `sortino_window`, compute annualized excess return
  (mean daily log return - target_daily) * 252, and downside deviation =
  sqrt(mean(min(0, r - target_daily)^2)) * sqrt(252) (annualized).
- Sortino = annualized_excess_return / (downside_deviation + adjustment),
  guarded against a near-zero denominator.
- Exposure: scale = clip(sortino / sortino_reference, 0, leverage_cap).
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


def _rolling_sortino(
    close: pd.Series, window: int, target_daily: float, adjustment: float
) -> pd.Series:
    """Rolling Sortino Ratio: annualized excess return over annualized
    downside deviation (semi-deviation below target_daily)."""
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
        mean_daily = float(np.mean(seg))
        annualized_excess = (mean_daily - target_daily) * 252.0

        downside = np.clip(seg - target_daily, a_min=None, a_max=0.0)
        downside_var_daily = float(np.mean(downside ** 2))
        downside_dev_annualized = np.sqrt(downside_var_daily * 252.0)

        denom = downside_dev_annualized + adjustment
        if denom <= 1e-8:
            continue
        out[end] = annualized_excess / denom

    return pd.Series(out, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    sortino_window: int = 90,
    target_daily: float = 0.0,
    adjustment: float = 0.001,
    sortino_reference: float = 1.0,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    sortino = _rolling_sortino(close, sortino_window, target_daily, adjustment)

    raw_exposure = (sortino / sortino_reference).astype(float)
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
