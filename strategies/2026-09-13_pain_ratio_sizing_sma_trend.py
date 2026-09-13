"""Strategy: SMA200 trend-following gate with rolling Pain Ratio (Zephyr,
average-drawdown-based) dynamic exposure scaling.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per https://breakingdownfinance.com/finance-topics/performance-measurement/zephyr-pain-index/
(Becker & Moore, Zephyr Associates 2006; read via browser_exec this
iteration), the Pain Index is the AVERAGE drawdown over a trailing window
(mean of D(t), not the MAXIMUM like MaxDD/MAR-ratio, and not the RMS like
the Ulcer Index -- a third, distinct way of aggregating the drawdown
series). The Pain Ratio = excess return / Pain Index, analogous to the
Calmar/MAR ratio but substituting average drawdown for max drawdown.

This repo already has an accepted MAR-ratio (max-drawdown-based) sizing
overlay (2026-09-13-047) and an accepted/rejected static-threshold Ulcer
Index (RMS-drawdown-based) entry filter (2026-09-04-144, 2026-09-10-045)
-- this iteration isolates whether the THIRD drawdown-aggregation method
(simple average) used as a dynamic SIZING signal (following this repo's
established sizing-overlay pattern, not a discrete entry filter) performs
differently on the same SMA(200) trend gate. Average drawdown is less
sensitive to a single extreme drawdown event than either MAX or RMS
aggregation, which may make it more robust on crypto's occasional flash-
crash tail events specifically. First Pain-Ratio/Pain-Index-based sizing
strategy in this repo.

Signal logic
------------
- Base directional signal: long when close > SMA(trend_window), flat
  otherwise (identical trend gate to the repo's other sizing-overlay
  strategies).
- Rolling Pain Index over `pain_window` days: mean of the drawdown series
  D(t) = (running_peak(t) - price(t)) / running_peak(t), computed within
  the trailing window (running peak reset to the window's own max, per
  the standard Pain Index convention of measuring drawdown relative to
  the highest price observed so far WITHIN the evaluation window).
- Rolling annualized return over the same window (mean daily log return *
  252).
- Pain Ratio = annualized_return / pain_index (guarded against zero/tiny
  pain_index).
- Exposure: scale = clip(pain_ratio / pain_ratio_reference, 0,
  leverage_cap). Applied only while the trend gate is long.

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


def _rolling_pain_ratio(close: pd.Series, window: int) -> pd.Series:
    """Rolling Pain Ratio: annualized mean daily log return / Pain Index
    (average drawdown within the window), vectorized via numpy sliding
    windows."""
    values = close.to_numpy(dtype=float)
    n = len(values)
    out = np.full(n, np.nan)
    if n < window:
        return pd.Series(out, index=close.index)

    price_windows = np.lib.stride_tricks.sliding_window_view(values, window)
    running_peak = np.maximum.accumulate(price_windows, axis=1)
    drawdowns = (running_peak - price_windows) / running_peak
    pain_index = np.nanmean(drawdowns, axis=1)

    log_ret = np.log(close / close.shift(1)).to_numpy(dtype=float)
    ret_windows = np.lib.stride_tricks.sliding_window_view(log_ret, window)
    mean_daily_ret = np.nanmean(ret_windows, axis=1)
    annualized_ret = mean_daily_ret * 252.0

    with np.errstate(divide="ignore", invalid="ignore"):
        pain_ratio = np.where(pain_index > 1e-6, annualized_ret / pain_index, np.nan)

    out[window - 1:] = pain_ratio
    return pd.Series(out, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    pain_window: int = 90,
    pain_ratio_reference: float = 3.0,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    pain_ratio = _rolling_pain_ratio(close, pain_window)

    raw_exposure = (pain_ratio / pain_ratio_reference).astype(float)
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
