"""Strategy: Lo-MacKinlay Variance Ratio trend-regime gate + Donchian breakout.

Hypothesis (knowledge_base id=2026-09-08-104): Direct follow-up to
2026-09-08-103 (VR(k) gate + EMA crossover, rejected -- full-sample Sharpe
0.443 QQQ / 0.391 SPY, both below threshold, with the note that "the
crossover mechanism itself may be diluting whatever edge the regime
filter contributes"). This iteration keeps the same Lo-MacKinlay Variance
Ratio VR(k) = Var(k-period return) / (k * Var(1-period return)) trending-
regime gate (VR(k) >= vr_threshold => statistically-trending regime, per
Lo & MacKinlay 1988 / https://twowaymind.com/article-variance-ratio), but
swaps the entry mechanism for the already-accepted-on-QQQ Donchian Channel
breakout (2026-09-04-054: buy at close on a new N-day high, exit on a new
M-day low), isolating whether the VR(k) regime filter improves on the
plain (ungated) Donchian breakout specifically, or whether VR(k) itself
carries no exploitable signal regardless of the entry mechanism used.

Signal logic
------------
- Rolling VR(k) computed identically to 2026-09-08-103 (same
  _rolling_variance_ratio implementation).
- Trending regime = VR(k) >= vr_threshold.
- Entry (long): close makes a new entry_window-day high AND the bar is in
  a trending regime.
- Exit: close makes a new exit_window-day low, OR the regime flips out of
  "trending" (VR(k) < vr_threshold), OR a max_hold_days time-stop backstop.

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
    """Rolling Lo-MacKinlay Variance Ratio VR(k) (same construction as
    2026-09-08_variance_ratio_trend_regime_gate.py)."""
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
    entry_window: int = 20,
    exit_window: int = 10,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    vr = _rolling_variance_ratio(close, vr_k, vr_window)
    trending_regime = (vr >= vr_threshold).fillna(False)

    rolling_high = close.rolling(entry_window).max()
    rolling_low = close.rolling(exit_window).min()

    new_high = close >= rolling_high
    new_low = close <= rolling_low

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    new_high_v = new_high.values
    new_low_v = new_low.values
    trending_v = trending_regime.values

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(new_low_v[i]) or (not bool(trending_v[i])) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        if bool(new_high_v[i]) and bool(trending_v[i]):
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
