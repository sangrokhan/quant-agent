"""Strategy: Fractal Dimension Index (FDI) trend-strength gate for SMA crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-015):
The Fractal Dimension Index (Benoit Mandelbrot, "The Misbehavior of Markets")
measures how "fractal"/self-similar a price series is over a rolling window,
oscillating between 1.0 (perfectly directional/straight-line) and 2.0
(maximally noisy/ranging). Per https://www.quantifiedstrategies.com/
fractal-dimension-index/: readings above 1.5 indicate a ranging market,
below 1.5 a trending market, and below 1.3 an "unsustainable" near-straight
move likely to revert/pause. We use FDI as a trend-strength REGIME GATE for
a plain fast/slow SMA crossover: only take the crossover signal when FDI is
in the "sustainable trend" band (1.3 <= FDI <= fdi_trend_ceiling, i.e.
trending but not so straight-line it's about to exhaust), skipping both
ranging markets (FDI > ceiling) and unsustainable/exhausted moves (FDI <
1.3) where a fresh crossover is less likely to persist.

This is a novel indicator family for this repo -- prior trend-strength
gates used ADX (Wilder directional-movement-based), Choppiness Index
(log-normalized ATR-sum-vs-range ratio), or VHF (max-min range vs sum of
absolute changes); FDI instead uses a fractal box-counting/self-similarity
measure of the price path's own "roughness" via half-window range ratios,
a mathematically distinct construction (Hausdorff-dimension-inspired, not
directional-movement or range-efficiency based).

Signal logic
------------
- FDI over a rolling `fdi_window` (must be even), computed via the standard
  box-counting approximation: split the window into two halves, compute the
  "length" of each half (sum of |high-low| range per half, normalized by
  half-window-size) plus the full-window length; FDI = (log(L1+L2) -
  log(L)) / log(2), clipped to [1.0, 2.0]. This is the widely-documented
  Ehlers/Mandelbrot two-segment approximation used across the trading
  literature (avoids full computationally-expensive box-counting).
- Trend regime: `1.3 <= FDI <= fdi_ceiling` (default ceiling 1.5, i.e. the
  source's own "trending market" threshold).
- Entry (long): fast SMA crosses above slow SMA while in the trend regime.
- Exit: fast SMA crosses back below slow SMA, OR FDI regime breaks (rises
  above `fdi_ceiling`, i.e. market turns choppy/ranging), OR a
  `max_hold_days` time-stop.

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


def _fractal_dimension_index(high: pd.Series, low: pd.Series, window: int) -> pd.Series:
    """Two-segment box-counting FDI approximation, standard construction.

    window must be even; each rolling window is split into two equal
    halves, and each half's "length" is measured as the (high-low) range
    normalized by half-window bar count. FDI = (log(L1+L2) - log(L)) / log(2),
    clipped to the theoretical [1.0, 2.0] range.
    """
    if window % 2 != 0:
        window += 1
    half = window // 2

    n = len(high)
    hi = high.values.astype(float)
    lo = low.values.astype(float)
    fdi = np.full(n, np.nan)

    for t in range(window - 1, n):
        seg = slice(t - window + 1, t + 1)
        seg1 = slice(t - window + 1, t - window + 1 + half)
        seg2 = slice(t - half + 1, t + 1)

        def _len(hi_slice, lo_slice, m):
            rng = float(np.max(hi_slice) - np.min(lo_slice))
            return rng / m if m > 0 else 0.0

        n1 = _len(hi[seg1], lo[seg1], half)
        n2 = _len(hi[seg2], lo[seg2], half)
        n3 = _len(hi[seg], lo[seg], window)

        if n1 <= 0 or n2 <= 0 or n3 <= 0:
            fdi[t] = np.nan
            continue
        val = (math.log(n1 + n2) - math.log(n3)) / math.log(2)
        fdi[t] = min(max(val, 1.0), 2.0)

    return pd.Series(fdi, index=high.index)


def generate_signals(
    price_df: pd.DataFrame,
    fdi_window: int = 30,
    fdi_ceiling: float = 1.5,
    fdi_floor: float = 1.3,
    fast_sma: int = 20,
    slow_sma: int = 50,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    fdi = _fractal_dimension_index(high, low, window=fdi_window)
    trend_regime = (fdi >= fdi_floor) & (fdi <= fdi_ceiling)

    fast = close.rolling(fast_sma).mean()
    slow = close.rolling(slow_sma).mean()
    bullish_cross = (fast > slow) & (fast.shift(1) <= slow.shift(1))
    bearish_cross = (fast < slow) & (fast.shift(1) >= slow.shift(1))

    entry = bullish_cross & trend_regime.fillna(False)
    exit_cross = bearish_cross
    exit_regime = ~trend_regime.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or bool(exit_regime.iloc[i]) or held >= max_hold_days:
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
