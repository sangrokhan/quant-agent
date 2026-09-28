"""Strategy: Dual ALMA (Arnaud Legoux Moving Average) crossover, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-28-050):
ALMA (Torrie/Legoux/Arnaud, 2009) is a Gaussian-weighted moving average with
an offset parameter that lets it hug price more closely than a plain SMA/EMA
while still filtering high-frequency noise, aiming to reduce both lag AND
overshoot simultaneously (unlike EMA which reduces lag at the cost of more
overshoot, or SMA which has neither but lags heavily). Per TradingView's
"Arnaud Legoux Moving Average Cross (ALMA)" open-source script (Marianne9,
2022) -- read via browser_exec this iteration (web_search DDGS backend
returned no results for the initial ALMA query) -- the standard mechanical
trading rule is a dual-ALMA crossover: a fast-length ALMA crossing above a
slow-length ALMA signals a long entry (the source's own volume filter is
omitted here since this repo's interface has no volume-based gate
convention beyond what strategy code itself computes, and the script itself
notes it can be adapted to non-crypto instruments). Corroborated by the
Google SERP snippet quoting LuxAlgo's ALMA guide: "A two-average crossover,
a faster ALMA against a..." (slower ALMA) as the standard approach beyond
naive price-crosses-single-ALMA (flagged by the same snippet as the most
whipsaw-prone variant). First ALMA-family strategy in this repo (0 prior
hits per strategies_index.jsonl keyword search).

ALMA formula (per the original Arnaud Legoux / Dickson definition, widely
reproduced e.g. by TradingView/LuxAlgo docs):
    m = floor(offset * (window - 1))         # offset in [0, 1], default 0.85
    s = window / sigma                        # sigma controls Gaussian width, default 6
    w_i = exp(-((i - m)^2) / (2 * s^2))  for i in [0, window-1]
    ALMA_t = sum(w_i * price[t - window + 1 + i]) / sum(w_i)

Signal logic (daily bars, causal/no look-ahead):
1. Compute ALMA(fast_window) and ALMA(slow_window) on close, both with the
   same offset/sigma shape parameters.
2. Long entry: fast ALMA crosses above slow ALMA (golden cross).
3. Exit: fast ALMA crosses back below slow ALMA (death cross), or a
   max_hold_days time-stop (added robustness backstop, not in the original
   script, consistent with this repo's established convention for crossover
   strategies that can otherwise stay in a single trade indefinitely).

Interface contract for validators (see validation/validators.py) and
validation/grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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


def _alma(series: pd.Series, window: int, offset: float = 0.85, sigma: float = 6.0) -> pd.Series:
    """Arnaud Legoux Moving Average, causal (no look-ahead)."""
    if window < 1:
        raise ValueError("window must be >= 1")
    m = math.floor(offset * (window - 1))
    s = window / sigma
    idx = np.arange(window)
    weights = np.exp(-((idx - m) ** 2) / (2 * s * s))
    weights = weights / weights.sum()

    values = series.to_numpy(dtype=float)
    n = len(values)
    out = np.full(n, np.nan)
    for t in range(window - 1, n):
        window_slice = values[t - window + 1 : t + 1]
        if np.any(np.isnan(window_slice)):
            continue
        out[t] = float(np.dot(window_slice, weights))
    return pd.Series(out, index=series.index)


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 9,
    slow_window: int = 21,
    offset: float = 0.85,
    sigma: float = 6.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fast_alma = _alma(close, fast_window, offset=offset, sigma=sigma)
    slow_alma = _alma(close, slow_window, offset=offset, sigma=sigma)

    cross_up = (fast_alma > slow_alma) & (fast_alma.shift(1) <= slow_alma.shift(1))
    cross_down = (fast_alma < slow_alma) & (fast_alma.shift(1) >= slow_alma.shift(1))

    cross_up = cross_up.fillna(False)
    cross_down = cross_down.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    n = len(close)

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]):
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
