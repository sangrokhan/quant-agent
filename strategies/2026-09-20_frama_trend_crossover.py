"""Strategy: Fractal Adaptive Moving Average (FRAMA, John Ehlers) trend
crossover, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per prorealcode.com's "Ehler's Fractal Adaptive Moving Average (FRAMA)"
page (visited this iteration via browser_exec, web_search DDGS backend
TLS-connection-errored on the query; several candidate FRAMA sources
404'd: quantifiedstrategies.com, aemmtrader.com, metatrader5.com), FRAMA is
an EMA whose smoothing factor (alpha) adapts dynamically based on the
FRACTAL DIMENSION of recent price action: split the lookback window into
two halves, compute each half's own high-low-range-per-bar (N1, N2) plus
the whole window's range-per-bar (N3), derive the fractal dimension
Dimen = (log(N1+N2) - log(N3)) / log(2), then alpha = exp(-4.6*(Dimen-1))
(clamped to [0.01, 1]). Low fractal dimension (Dimen near 1, a smooth/
directional price path) => alpha near 1 => FRAMA hugs price tightly and
reacts fast; high fractal dimension (Dimen near 2, choppy/range-bound price)
=> alpha near 0.01 => FRAMA flattens out, filtering noise. The source's own
disclosed interpretation: "The FRAMA line has a greater reactivity to
changes in trends than moving averages, making it possible to take a much
earlier position on a breakout" -- i.e. FRAMA is meant to be traded like
any other moving-average trend-follower (price crossing the FRAMA line),
but with the claimed advantage of filtering false signals during
consolidation (low Dimen periods) automatically via its own adaptive
smoothing.

Distinct from every other adaptive-moving-average strategy already in this
repo (KAMA, VIDYA, dual-KAMA, etc. use volatility/efficiency-ratio-based
adaptation): FRAMA's adaptation is keyed specifically to the FRACTAL
DIMENSION of the high-low range (a self-similarity/roughness measure, not
a volatility or efficiency-ratio measure). 0 prior FRAMA entries in this
repo.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _frama(close: pd.Series, high: pd.Series, low: pd.Series, length: int, w: float = -4.6) -> pd.Series:
    """Ehlers' Fractal Adaptive Moving Average.

    `length` must be even (per Ehlers' original construction, which splits
    the window into two equal halves).
    """
    length = length if length % 2 == 0 else length + 1
    half = length // 2
    n = len(close)

    high_vals = high.values
    low_vals = low.values
    close_vals = close.values
    frama = np.full(n, np.nan)

    for i in range(length - 1, n):
        window_high = high_vals[i - length + 1: i + 1]
        window_low = low_vals[i - length + 1: i + 1]

        n3 = (window_high.max() - window_low.min()) / length

        first_half_high = window_high[:half]
        first_half_low = window_low[:half]
        n1 = (first_half_high.max() - first_half_low.min()) / half

        second_half_high = window_high[half:]
        second_half_low = window_low[half:]
        n2 = (second_half_high.max() - second_half_low.min()) / half

        if n1 > 0 and n2 > 0 and n3 > 0:
            dimen = (np.log(n1 + n2) - np.log(n3)) / np.log(2)
        else:
            dimen = 1.0

        alpha = np.exp(w * (dimen - 1))
        alpha = min(max(alpha, 0.01), 1.0)

        if i == length - 1:
            frama[i] = close_vals[i]
        else:
            frama[i] = alpha * close_vals[i] + (1 - alpha) * frama[i - 1]

    return pd.Series(frama, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 20,
    w: float = -4.6,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: close crosses above the FRAMA line.
    Exit to flat: close crosses below the FRAMA line.
    Standard moving-average crossover interpretation, per the source's own
    stated usage ("interpretation of the indicator is identical to the
    interpretation of moving averages").
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    frama = _frama(close, high, low, length=length, w=w)
    above = close > frama
    position = above.fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
