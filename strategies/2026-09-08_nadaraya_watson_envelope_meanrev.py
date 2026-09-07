"""Strategy: Nadaraya-Watson Envelope (kernel-regression band) mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-014):
A causal (non-repainting/"endpoint") Nadaraya-Watson kernel regression of
recent closes, banded by mult * mean-absolute-deviation of the fit residual,
identifies short-term price "stretch" from its local kernel-smoothed trend.
Per LuxAlgo's official docs (https://www.luxalgo.com/library/indicator/
nadaraya-watson-envelope/): "Price crosses the lower extremity: ... flagging
stretched declines for mean-reversion longs." We test the long-only
mean-reversion interpretation, gated by a long-term SMA trend filter (avoid
fading a structural downtrend, per the source's own caveat that "extremity
crossings describe stretch, not guaranteed reversals").

This is a novel indicator family for this repo -- the Gaussian-kernel-
weighted regression + mean-absolute-deviation envelope construction is
distinct from the Bollinger/Keltner/STARC/Moving-Average-Envelope SMA-based
band families already tested (those use rolling std-dev or ATR around a
plain SMA/EMA basis, not a kernel-regression fit with per-bar Gaussian
distance-decay weights).

Signal logic
------------
- Causal Nadaraya-Watson fit: for each bar t, fit[t] is a Gaussian-kernel-
  weighted average of the last `window` closes (weights decay with distance
  from the current bar via bandwidth `h` -- larger h = smoother fit). This
  is the "endpoint estimator" LuxAlgo recommends for non-repainting/
  real-time use (as opposed to the default two-sided smoothing fit, which
  would look ahead and is not usable for a genuine backtest).
- mae[t] = mean absolute deviation of the last `window` closes from fit[t].
- lower_band = fit - mult * mae; upper_band = fit + mult * mae.
- Entry (long): close crosses below lower_band AND close > SMA(trend_window)
  (long-term uptrend filter, avoids fading a genuine downtrend per source's
  own stated caveat).
- Exit: close crosses back above fit (kernel-regression center, the mean-
  reversion target) OR trend filter breaks OR max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 long/flat)
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _nw_envelope(close: pd.Series, window: int, h: float, mult: float):
    """Causal (endpoint) Nadaraya-Watson kernel regression fit + envelope.

    For each bar t (t >= window-1), fit[t] is a Gaussian-kernel-weighted
    average of close[t-window+1 : t+1], weights decaying with distance from
    the endpoint (bar t itself) -- this only ever looks backward, so it is
    the non-repainting variant LuxAlgo describes for real-time/backtest use.
    """
    n = len(close)
    vals = close.values.astype(float)
    fit = np.full(n, np.nan)
    mae = np.full(n, np.nan)

    # Precompute Gaussian kernel weights for distances 0..window-1
    dist = np.arange(window)
    weights = np.exp(-(dist ** 2) / (2.0 * h * h))
    w_sum = weights.sum()

    for t in range(window - 1, n):
        segment = vals[t - window + 1: t + 1]  # oldest..newest
        # weight[i] applies to the bar `dist[i]` steps before the endpoint
        # i.e. reversed segment aligned with dist=0 at the endpoint (t)
        rev = segment[::-1]  # rev[0] = vals[t] (endpoint), rev[k] = vals[t-k]
        fit_t = float(np.dot(rev, weights) / w_sum)
        fit[t] = fit_t
        mae[t] = float(np.mean(np.abs(segment - fit_t)))

    fit_s = pd.Series(fit, index=close.index)
    mae_s = pd.Series(mae, index=close.index)
    upper = fit_s + mult * mae_s
    lower = fit_s - mult * mae_s
    return fit_s, upper, lower


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 20,
    h: float = 6.0,
    mult: float = 2.5,
    trend_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fit, upper, lower = _nw_envelope(close, window=window, h=h, mult=mult)
    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    entry = (close < lower) & uptrend.fillna(False)
    exit_meanrev = close > fit
    exit_trend_break = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
