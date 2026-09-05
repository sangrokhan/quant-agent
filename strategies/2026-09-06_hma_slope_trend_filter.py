"""Strategy: Hull Moving Average (HMA) slope-based trend filter, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-097),
sourced from https://www.luxalgo.com (LuxAlgo Indicator Library, "HMA:
Trend Concept"): "As a slope-based trend filter: take longs only while
the HMA rises and shorts only while it falls." Corroborated by
Capital.com/GoCharting/marketindicatorlab.com describing HMA slope
direction as the primary trend signal (distinct from the "color change"
implementation detail, which per marketindicatorlab.com is "not a
separate calculation" -- just a visual encoding of the same slope sign).

Distinct from this repo's already-tested price-crosses-HMA strategy
(2026-09-04-026, near-miss, close crossing above/below the HMA line) --
this variant uses the HMA's OWN SLOPE turning positive/negative as the
entry/exit trigger rather than price relative to the HMA line. Slope-based
triggers should fire earlier/differently than price-crossing triggers
(the HMA itself must start turning, independent of where price currently
sits relative to it).

Signal logic
------------
- HMA(hma_window) = WMA(2*WMA(close, hma_window/2) - WMA(close,
  hma_window), sqrt(hma_window)) (standard Alan Hull construction).
- Long entry: HMA slope turns from non-positive to positive (HMA[t] >
  HMA[t-1] AND HMA[t-1] <= HMA[t-2]).
- Exit: HMA slope turns from non-negative to negative (HMA[t] < HMA[t-1]
  AND HMA[t-1] >= HMA[t-2]), or a max_hold_days time-stop (repo standard
  safety valve).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, position lagged by 1 day to avoid look-ahead bias)
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


def _wma(series: pd.Series, window: int) -> pd.Series:
    """Fast linear-weighted moving average via convolution (equivalent to
    the naive rolling-apply weighted-average formula, but vectorized)."""
    weights = np.arange(1, window + 1, dtype=float)
    weights = weights / weights.sum()
    vals = series.values.astype(float)
    n = len(vals)
    out = np.full(n, np.nan)
    if n >= window:
        conv = np.convolve(vals, weights[::-1], mode="valid")
        out[window - 1:] = conv
    return pd.Series(out, index=series.index)


def _hma(close: pd.Series, window: int) -> pd.Series:
    half = max(int(window / 2), 1)
    sqrt_w = max(int(math.sqrt(window)), 1)
    wma_half = _wma(close, half)
    wma_full = _wma(close, window)
    raw = 2 * wma_half - wma_full
    hma = _wma(raw, sqrt_w)
    return hma


def generate_signals(
    price_df: pd.DataFrame,
    hma_window: int = 20,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    hma = _hma(close, hma_window)
    hma_prev = hma.shift(1)
    hma_prev2 = hma.shift(2)

    slope_turns_up = (hma > hma_prev) & (hma_prev <= hma_prev2)
    slope_turns_down = (hma < hma_prev) & (hma_prev >= hma_prev2)

    entry_signal = slope_turns_up.fillna(False).values
    exit_signal = slope_turns_down.fillna(False).values

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0

    for i in range(len(df.index)):
        if in_position:
            hold_count += 1
            if exit_signal[i] or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_signal[i]:
                in_position = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **params)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
