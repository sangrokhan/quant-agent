"""Strategy: SMA200 trend-following gate with rolling Serenity Ratio
dynamic exposure scaling.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per https://portfoliometrics.net/metrics/serenity-ratio (visited this
iteration via browser_exec Google SERP fallback), the Serenity Ratio
combines return, drawdown depth/duration, AND tail-risk into a single
risk-adjusted metric, distinguishing it from every other risk-ratio sizing
overlay already tested in this repo (Sterling, Burke, Pain, MAR/Calmar,
Omega, Cornish-Fisher Modified Sharpe, K-Ratio, Tail-Ratio, Rachev,
Treynor, UPI/Martin, Kappa-3, Sortino, Downside Deviation):

    Serenity Ratio = (R_p - R_f) / (Ulcer_Index * Pitfall)
    Ulcer_Index = sqrt(mean(drawdown_pct^2))    (quadratic mean of drawdowns,
                                                  already used standalone in
                                                  this repo's Ulcer Index /
                                                  Ulcer Performance Index
                                                  entries, e.g. as UPI's
                                                  denominator)
    Pitfall = CDaR / sigma_p
    CDaR = Conditional Drawdown at Risk = mean of the worst
           (1 - cdar_alpha) fraction of per-bar drawdowns (a CVaR taken
           over the DRAWDOWN distribution rather than the RETURN
           distribution -- this is the genuinely novel ingredient no prior
           entry in this repo has used)
    sigma_p = trailing std of daily returns

Serenity's Pitfall term is the first CDaR-based (Conditional Drawdown at
Risk) construction in this repo -- distinct from CVaR-of-RETURNS already
used elsewhere, since CDaR operates on the DRAWDOWN series specifically,
capturing tail-risk concentrated in the worst pullback periods rather than
the worst single-day returns. First Serenity Ratio strategy in this repo.

This strategy scales an SMA(200) trend gate's exposure by the trailing
Serenity Ratio, following this repo's established risk-ratio-sizing-overlay
template (see e.g. strategies/2026-09-13_sterling_ratio_sizing_sma_trend.py).

Signal logic
------------
- Base directional signal: long when close > SMA(trend_window), flat
  otherwise.
- Within each trailing `serenity_window`:
  - drawdown series D(t) = (running_peak - price) / running_peak
  - Ulcer Index = sqrt(mean(D(t)^2))
  - CDaR = mean of the worst (1 - cdar_alpha) fraction of D(t) values
    (e.g. cdar_alpha=0.95 -> average of the worst 5% of drawdown readings)
  - sigma_p = std of daily log returns over the same window
  - Pitfall = CDaR / sigma_p
  - annualized_return = mean(daily log return) * 252
  - Serenity Ratio = annualized_return / (Ulcer_Index * Pitfall + adjustment)
- Exposure: scale = clip(serenity_ratio / serenity_reference, 0,
  leverage_cap). Applied only while the trend gate is long.

Interface contract for validators (see validation/validators.py) and the
grid tester (see validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series   (continuous exposure
        in [0, leverage_cap])
    generate_returns(price_df, **params) -> pd.Series   (daily returns)
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


def _rolling_serenity_ratio(
    close: pd.Series,
    window: int,
    cdar_alpha: float,
    adjustment: float,
) -> pd.Series:
    """Rolling Serenity Ratio = annualized_return / (Ulcer_Index * Pitfall).

    Pitfall = CDaR / sigma_p, CDaR = mean of the worst (1-cdar_alpha)
    fraction of per-bar drawdown readings within the window.
    """
    values = close.to_numpy(dtype=float)
    n = len(values)
    out = np.full(n, np.nan)
    if n < window:
        return pd.Series(out, index=close.index)

    log_ret = np.log(close / close.shift(1)).to_numpy(dtype=float)

    for end in range(window - 1, n):
        start = end - window + 1
        seg = values[start:end + 1]
        running_peak = np.maximum.accumulate(seg)
        dd = (running_peak - seg) / running_peak

        ulcer_index = float(np.sqrt(np.nanmean(dd ** 2)))

        n_tail = max(1, int(np.ceil((1.0 - cdar_alpha) * len(dd))))
        dd_sorted = np.sort(dd)[::-1]
        cdar = float(np.mean(dd_sorted[:n_tail]))

        ret_seg = log_ret[start:end + 1]
        sigma_p = float(np.nanstd(ret_seg))
        pitfall = cdar / sigma_p if sigma_p > 1e-8 else np.nan

        mean_daily_ret = float(np.nanmean(ret_seg))
        annualized_ret = mean_daily_ret * 252.0

        denom = ulcer_index * pitfall + adjustment if pd.notna(pitfall) else np.nan
        out[end] = annualized_ret / denom if pd.notna(denom) and denom > 1e-6 else np.nan

    return pd.Series(out, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    serenity_window: int = 90,
    cdar_alpha: float = 0.90,
    serenity_adjustment: float = 0.02,
    serenity_reference: float = 1.5,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    serenity = _rolling_serenity_ratio(close, serenity_window, cdar_alpha, serenity_adjustment)

    raw_exposure = (serenity / serenity_reference).astype(float)
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
