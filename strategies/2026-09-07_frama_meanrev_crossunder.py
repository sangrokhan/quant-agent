"""Strategy: FRAMA (Fractal Adaptive Moving Average) crossunder mean-reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-027):
Source: https://www.quantifiedstrategies.com/fractal-adaptive-moving-average-frama/
(accessed 2026-09-07).

The source's own SPY backtests of a plain N-day moving average (not even
FRAMA yet, plain SMA/EMA-style crossover) found that a MEAN-REVERSION rule
(buy when close crosses BELOW the average, sell when it crosses back ABOVE)
consistently outperformed the more commonly tried TREND-FOLLOWING direction
(buy on cross above, sell on cross below) across every tested period
(5,10,25,50,100,200 days) -- e.g. period=25: mean-reversion CAGR 8.66% vs
trend-following CAGR 1.04%, similar pattern for MDD. This is the first
FRAMA strategy in this repo (0 prior FRAMA entries in
knowledge_base/strategies_index.jsonl).

FRAMA (John Ehlers) is an adaptive EMA whose smoothing factor responds to
the market's local fractal dimension: it tracks price closely during
strong trends (low fractal dimension, high alpha) and flattens out during
choppy/ranging conditions (high fractal dimension, low alpha) -- unlike a
fixed-span SMA/EMA. This strategy tests whether swapping in FRAMA (instead
of the source's plain SMA) as the reference average, while keeping the
source's own discovered MEAN-REVERSION crossunder/crossover direction,
retains or improves on that edge, since FRAMA should track price more
tightly in trends and flatten in chop -- potentially giving cleaner
mean-reversion signals than a fixed-span average.

FRAMA calculation (standard Ehlers formulation; the smoothing-factor
formula FRAMA_t = alpha*Price_t + (1-alpha)*FRAMA_{t-1},
alpha = exp(-4.6*(D-1)) is explicitly given by the source; the fractal
dimension D itself is computed via the standard two-half-window
high-low-range method, alpha clipped to [alpha_min, 1] for numerical
stability, a standard implementation detail not itself a methodology
change):
    N1 = (max(high, w/2) - min(low, w/2)) / (w/2)   [first half of window]
    N2 = (max(high, w/2) - min(low, w/2)) / (w/2)   [second half of window]
    N3 = (max(high, w)   - min(low, w))   / w        [full window]
    D  = (log(N1+N2) - log(N3)) / log(2)
    alpha = clip(exp(-4.6*(D-1)), alpha_min, 1.0)

Signal logic
------------
- Compute FRAMA(frama_window) on close (using high/low for the fractal
  dimension calc).
- Entry (long): close crosses from >= FRAMA to < FRAMA (mean-reversion
  buy-the-dip-below-average signal, per source's discovered direction).
- Exit: close crosses back above FRAMA, or after max_hold_days (avoid
  indefinite holds if FRAMA itself drifts down with price in a real
  downtrend rather than mean-reverting).

Interface contract for validators (see validation/validators.py):
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


def _frama(df: pd.DataFrame, frama_window: int = 16, alpha_min: float = 0.01) -> pd.Series:
    """Compute the Ehlers FRAMA series. frama_window must be even."""
    if frama_window % 2 != 0:
        frama_window += 1
    half = frama_window // 2

    high = df["high"]
    low = df["low"]
    close = df["close"]

    n1 = (high.rolling(half).max() - low.rolling(half).min()) / half

    high_shifted = high.shift(half)
    low_shifted = low.shift(half)
    n2 = (high_shifted.rolling(half).max() - low_shifted.rolling(half).min()) / half

    n3 = (high.rolling(frama_window).max() - low.rolling(frama_window).min()) / frama_window

    with np.errstate(divide="ignore", invalid="ignore"):
        sum_n1_n2 = n1 + n2
        dim = np.where(
            (sum_n1_n2 > 0) & (n3 > 0),
            (np.log(sum_n1_n2) - np.log(n3)) / np.log(2),
            1.0,
        )
    dim = pd.Series(dim, index=df.index).clip(lower=1.0, upper=2.0)

    alpha = np.exp(-4.6 * (dim - 1.0)).clip(lower=alpha_min, upper=1.0)

    frama = pd.Series(index=df.index, dtype=float)
    close_vals = close.to_numpy()
    alpha_vals = alpha.to_numpy()
    frama_vals = np.empty(len(close_vals), dtype=float)

    warmup = frama_window
    frama_vals[:warmup] = np.nan
    if len(close_vals) > warmup:
        frama_vals[warmup] = close_vals[warmup]
        for i in range(warmup + 1, len(close_vals)):
            a = alpha_vals[i]
            if np.isnan(a):
                a = alpha_min
            frama_vals[i] = a * close_vals[i] + (1 - a) * frama_vals[i - 1]
    frama[:] = frama_vals
    return frama


def generate_signals(
    price_df: pd.DataFrame,
    frama_window: int = 16,
    alpha_min: float = 0.01,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    frama = _frama(df, frama_window=frama_window, alpha_min=alpha_min)

    below = close < frama
    crossed_below = below & (~below.shift(1).fillna(False))
    above = close >= frama
    crossed_above = above & (~above.shift(1).fillna(False))

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    pos_vals = np.zeros(len(df), dtype=int)
    crossed_below_vals = crossed_below.to_numpy()
    crossed_above_vals = crossed_above.to_numpy()
    frama_vals = frama.to_numpy()

    for i in range(len(df)):
        if np.isnan(frama_vals[i]):
            pos_vals[i] = 0
            continue
        if in_pos:
            hold_count += 1
            if crossed_above_vals[i] or hold_count >= max_hold_days:
                in_pos = False
                hold_count = 0
                pos_vals[i] = 0
            else:
                pos_vals[i] = 1
        else:
            if crossed_below_vals[i]:
                in_pos = True
                hold_count = 0
                pos_vals[i] = 1
            else:
                pos_vals[i] = 0

    position[:] = pos_vals
    return position


def generate_returns(
    price_df: pd.DataFrame,
    frama_window: int = 16,
    alpha_min: float = 0.01,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return daily strategy returns (no transaction costs applied)."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change()

    position = generate_signals(
        price_df,
        frama_window=frama_window,
        alpha_min=alpha_min,
        max_hold_days=max_hold_days,
    )
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret.fillna(0.0)
