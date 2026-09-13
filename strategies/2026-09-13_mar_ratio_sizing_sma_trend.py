"""Strategy: SMA200 trend-following gate with rolling MAR-ratio (Calmar
ratio) dynamic exposure scaling.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per https://www.ir-tracker.com/en/columns/advanced-strategy/drawdown-management
(read via browser_exec this iteration), the MAR ratio (a.k.a. Calmar ratio,
MAR = CAGR / MaxDD -- return earned per unit of maximum drawdown suffered)
is a standard professional risk-adjusted-return metric. This strategy tests
whether using the trailing MAR ratio of the underlying asset itself as a
DYNAMIC EXPOSURE SCALER (scale exposure UP when the asset's own recent
risk-adjusted performance, as measured by its trailing MAR ratio, has been
good; scale DOWN when it has been poor) on top of an SMA(200) trend gate
improves risk-adjusted returns versus a static full-size trend-following
position. This is a genuinely different sizing signal from the two prior
sizing overlays in this repo -- inverse-volatility targeting (2026-09-08-165,
scales by realized stddev) and CVaR-targeting (2026-09-13-045, scales by
tail-loss magnitude) -- because MAR ratio blends BOTH the return and the
risk side of the ledger into a single trailing performance-quality signal,
rather than sizing purely off a risk/dispersion measure. No prior MAR-ratio/
Calmar-ratio-based strategy exists in this repo.

Signal logic
------------
- Base directional signal: long when close > SMA(trend_window), flat
  otherwise (same trend gate as the repo's other accepted sizing-overlay
  strategies, isolating the sizing-mechanism variable).
- Rolling trailing MAR ratio over `mar_window` days: CAGR_approx = mean
  daily log return * 252 (annualized); MaxDD_approx = max drawdown of the
  cumulative price path within the trailing window. MAR = CAGR_approx /
  MaxDD_approx (guarded against zero/negative MaxDD).
- Exposure: scale = clip(MAR / mar_reference, 0, leverage_cap), where
  mar_reference is a normalizing constant (the MAR ratio level that maps
  to full 1.0x exposure). Applied only while the trend gate is long.

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


def _rolling_mar_ratio(close: pd.Series, window: int) -> pd.Series:
    """Rolling trailing MAR (Calmar) ratio of the underlying price series:
    annualized mean daily log return divided by the max drawdown observed
    within the trailing window. Vectorized via numpy sliding windows."""
    log_ret = np.log(close / close.shift(1))
    values = close.to_numpy(dtype=float)
    n = len(values)
    out = np.full(n, np.nan)
    if n < window:
        return pd.Series(out, index=close.index)

    price_windows = np.lib.stride_tricks.sliding_window_view(values, window)
    running_peak = np.maximum.accumulate(price_windows, axis=1)
    drawdowns = (running_peak - price_windows) / running_peak
    max_dd = np.nanmax(drawdowns, axis=1)

    log_ret_values = log_ret.to_numpy(dtype=float)
    ret_windows = np.lib.stride_tricks.sliding_window_view(log_ret_values, window)
    mean_daily_ret = np.nanmean(ret_windows, axis=1)
    annualized_ret = mean_daily_ret * 252.0

    with np.errstate(divide="ignore", invalid="ignore"):
        mar = np.where(max_dd > 1e-6, annualized_ret / max_dd, np.nan)

    out[window - 1:] = mar
    return pd.Series(out, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    mar_window: int = 90,
    mar_reference: float = 1.0,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    mar = _rolling_mar_ratio(close, mar_window)

    raw_exposure = (mar / mar_reference).astype(float)
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
