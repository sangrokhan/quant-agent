"""Strategy: Lo-MacKinlay Variance Ratio trending-regime gate + EMA crossover.

Hypothesis (knowledge_base id=2026-09-08-103): Per Lo & MacKinlay (1988)
and https://twowaymind.com/article-variance-ratio's summary: the Variance
Ratio VR(k) = Var(k-period return) / (k * Var(1-period return)) formally
tests the Random Walk Hypothesis by comparing how return variance scales
across time horizons. VR(k) > 1 signals positive return autocorrelation
(trending/momentum regime, "favorable for trend-following algorithms and
breakouts"); VR(k) < 1 signals negative autocorrelation (mean-reverting
regime, unfavorable for trend-following). This strategy gates a plain
fast/slow EMA crossover -- only taking the bullish crossover when the
market is in a statistically-trending regime per VR(k) -- on the theory
that trend-following signals should have more edge specifically when the
underlying return series exhibits genuine positive autocorrelation, rather
than trading the crossover unconditionally through regimes where the
market's own return-scaling behavior says trends shouldn't persist. First
Variance-Ratio-based strategy in this repo (distinct from the already-
tested Hurst-exponent regime gates, 2026-09-04-155/156, which use R/S
analysis rather than the Lo-MacKinlay variance-scaling test).

Signal logic
------------
- Rolling VR(k): over a trailing vr_window-day lookback of daily log
  returns, compute VR(k) = var(k-period cumulative log returns) /
  (k * var(1-period log returns)), per the source's own disclosed formula.
- Trending regime = VR(k) >= vr_threshold (source: VR(k) > 1 => trending;
  vr_threshold defaults to 1.0 but is tunable to require a stronger signal).
- Entry (long): fast EMA crosses above slow EMA WHILE in a trending regime.
- Exit: fast EMA crosses back below slow EMA, OR the regime flips out of
  "trending" (VR(k) < vr_threshold, risk-off regime-flip exit), OR a
  max_hold_days time-stop backstop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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


def _rolling_variance_ratio(close: pd.Series, k: int, vr_window: int) -> pd.Series:
    """Rolling Lo-MacKinlay Variance Ratio VR(k), computed over a trailing
    vr_window-day window of daily log returns, per the source's disclosed
    formula: VR(k) = Var(k-period log return) / (k * Var(1-period log return)).
    """
    log_price = np.log(close.replace(0, np.nan))
    r1 = log_price.diff()
    n = len(close)
    vr = pd.Series(np.nan, index=close.index)

    r1_vals = r1.values
    logp_vals = log_price.values

    for i in range(vr_window + k, n):
        start = i - vr_window
        window_r1 = r1_vals[start + 1: i + 1]
        window_r1 = window_r1[~np.isnan(window_r1)]
        if len(window_r1) < k * 3:
            continue
        mu = np.mean(window_r1)
        m1 = len(window_r1)
        var_1 = np.sum((window_r1 - mu) ** 2) / max(m1 - 1, 1)
        if var_1 <= 0:
            continue

        # k-period returns over the same window (log-price differenced by k)
        window_logp = logp_vals[start: i + 1]
        rk = window_logp[k:] - window_logp[:-k]
        rk = rk[~np.isnan(rk)]
        if len(rk) < 3:
            continue
        var_k = np.var(rk, ddof=1)

        vr.iloc[i] = var_k / (k * var_1)

    return vr


def generate_signals(
    price_df: pd.DataFrame,
    vr_k: int = 5,
    vr_window: int = 60,
    vr_threshold: float = 1.0,
    fast_ema: int = 10,
    slow_ema: int = 30,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    vr = _rolling_variance_ratio(close, vr_k, vr_window)
    trending_regime = (vr >= vr_threshold).fillna(False)

    ema_fast = close.ewm(span=fast_ema, adjust=False).mean()
    ema_slow = close.ewm(span=slow_ema, adjust=False).mean()
    bullish_cross = ema_fast > ema_slow

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    bullish_cross_v = bullish_cross.values
    trending_v = trending_regime.values

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if (not bool(bullish_cross_v[i])) or (not bool(trending_v[i])) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        if bool(bullish_cross_v[i]) and bool(trending_v[i]):
            in_position = True
            entry_idx = i
            position.iloc[i] = 1
        else:
            position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
