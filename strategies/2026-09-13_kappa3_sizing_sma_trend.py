"""Strategy: SMA200 trend-following gate with rolling Kappa-3 Ratio dynamic
exposure scaling.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per https://breakingdownfinance.com/finance-topics/performance-measurement/kappa-ratio/
(Kaplan and Knowles 2004, read via browser_exec Google SERP fallback after
web_search/DDGS didn't directly resolve the query): Kappa-n Ratio =
(mu - tau) / LPM_n(tau)^(1/n), where LPM_n(tau) is the n-th order Lower
Partial Moment of returns below threshold tau. Setting n=1 recovers the
Omega ratio - 1 (Omega already tested this cron trigger, 2026-09-13-049);
n=2 recovers the Sortino ratio (conceptually related to the already-tested
downside-deviation sizing overlay, 2026-09-13-048). n=3 (the standard
"Kappa 3" convention, cubing the downside deviations before averaging and
taking a cube root) puts EXTRA weight on the largest/most extreme downside
observations relative to n=1 or n=2, while still normalizing by an n-th
root (unlike the un-rooted higher-moment measures). First Kappa-3-based
sizing strategy in this repo -- genuinely distinct exponent from every
downside-risk measure tested so far.

Signal logic
------------
- Base directional signal: long when close > SMA(trend_window), flat
  otherwise (identical trend gate to the repo's other sizing-overlay
  strategies, for direct comparability).
- Within each trailing `kappa_window`, compute mu = mean daily log return
  (annualized: * 252), tau = threshold return (annualized, default 0), and
  LPM_3(tau) = mean(max(tau_daily - r, 0)^3) over the window (annualized by
  * 252 to match mu's scale, then cube-rooted).
- Kappa-3 = (mu - tau) / (LPM_3 * 252)^(1/3), guarded against a
  near-zero/degenerate denominator.
- Exposure: scale = clip(kappa3 / kappa3_reference, 0, leverage_cap).
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


def _rolling_kappa3(
    close: pd.Series, window: int, tau_daily: float, kappa_adjustment: float
) -> pd.Series:
    """Rolling Kappa-3 Ratio: annualized excess return over the cube root
    of the annualized 3rd-order Lower Partial Moment below tau_daily."""
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
        annualized_excess = (mean_daily - tau_daily) * 252.0

        shortfall = np.clip(tau_daily - seg, a_min=0.0, a_max=None)
        lpm3_daily = float(np.mean(shortfall ** 3))
        lpm3_annualized = lpm3_daily * 252.0
        denom = (lpm3_annualized ** (1.0 / 3.0)) + kappa_adjustment
        if denom <= 1e-8:
            continue
        out[end] = annualized_excess / denom

    return pd.Series(out, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    kappa_window: int = 90,
    tau_daily: float = 0.0,
    kappa_adjustment: float = 0.001,
    kappa3_reference: float = 1.0,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    kappa3 = _rolling_kappa3(close, kappa_window, tau_daily, kappa_adjustment)

    raw_exposure = (kappa3 / kappa3_reference).astype(float)
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
