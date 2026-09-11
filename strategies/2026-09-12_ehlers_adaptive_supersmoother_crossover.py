"""Strategy: Ehlers Adaptive SuperSmoother vs Fixed-Period SuperSmoother crossover.

Source: TASC (Technical Analysis of Stocks & Commodities) September 2026
Traders' Tips, John F. Ehlers "Improved Filter Performance", via TradingView
script description (https://www.tradingview.com/scripts/tasc/ index page,
"TASC 2026.09 Adaptive SuperSmoother", visited 2026-09-12, see
knowledge_base/visited_pages.jsonl).

Source's disclosed construction (a 2-pole SuperSmoother low-pass filter,
made adaptive by scaling its own critical period with its rate-of-change):

1. Compute a fixed-period 2-pole SuperSmoother filter (`base_period`,
   source default 20) on `close`.
2. Take the 1-bar rate-of-change (ROC) of that fixed filter, and compute its
   RMS (root-mean-square) over `rms_length` bars (source default 81).
3. Scale the ROC by that RMS, clip the scaled value to a max of 2.
4. Compute an adjustment factor = (1 - 0.5 * scaled_roc) ** 2.
5. adaptive_period = max(2, base_period * factor).
6. Compute a second SuperSmoother filter using this per-bar adaptive period
   -> the "Adaptive SuperSmoother".

Source's own disclosed trading rule: "long when the Adaptive SuperSmoother
is above the fixed-period SuperSmoother, and short [flat, long-only here]
otherwise." Exit is implicit (flip the other way); this repo adds a
`min_hold_days` hysteresis gate (same fix pattern successfully used for
several other Ehlers-filter/oscillator crossovers in this repo, e.g. Klinger
2026-09-04-085, ZLEMA 2026-09-06-171) to reduce whipsaw trade frequency, plus
an optional `max_hold_days` time-stop.

Novelty vs prior KB entries: distinct from the many prior SuperSmoother-based
strategies (all of which use ONE SuperSmoother as a price baseline/roofing
filter and cross it against price or a signal-line SMA) -- this compares TWO
SuperSmoothers (fixed-period vs a period that self-adapts based on the
fixed filter's own recent ROC/RMS), a genuinely different two-filter
divergence construction.

Interface contract (see validation/grid_test.py, validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _supersmoother(src: pd.Series, period: float) -> pd.Series:
    """Ehlers 2-pole SuperSmoother with a FIXED period (scalar)."""
    n = len(src)
    out = np.zeros(n)
    a1 = math.exp(-1.414 * math.pi / period)
    b1 = 2 * a1 * math.cos(1.414 * math.pi / period)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3
    vals = src.values
    for i in range(n):
        if i < 2 or np.isnan(vals[i - 1]) or np.isnan(vals[i - 2]):
            out[i] = vals[i]
        else:
            out[i] = c1 * (vals[i] + vals[i - 1]) / 2 + c2 * out[i - 1] + c3 * out[i - 2]
    return pd.Series(out, index=src.index)


def _supersmoother_adaptive(src: pd.Series, periods: pd.Series) -> pd.Series:
    """Ehlers 2-pole SuperSmoother with a per-bar-varying period series."""
    n = len(src)
    out = np.zeros(n)
    vals = src.values
    p = periods.values
    for i in range(n):
        period = max(2.0, float(p[i])) if not np.isnan(p[i]) else 20.0
        a1 = math.exp(-1.414 * math.pi / period)
        b1 = 2 * a1 * math.cos(1.414 * math.pi / period)
        c2 = b1
        c3 = -a1 * a1
        c1 = 1 - c2 - c3
        if i < 2 or np.isnan(vals[i - 1]) or np.isnan(vals[i - 2]):
            out[i] = vals[i]
        else:
            out[i] = c1 * (vals[i] + vals[i - 1]) / 2 + c2 * out[i - 1] + c3 * out[i - 2]
    return pd.Series(out, index=src.index)


def generate_signals(
    price_df: pd.DataFrame,
    base_period: int = 20,
    rms_length: int = 81,
    min_hold_days: int = 5,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fixed_ss = _supersmoother(close, float(base_period))

    roc = fixed_ss.diff()
    rms = (roc ** 2).rolling(rms_length).mean() ** 0.5
    scaled_roc = (roc / rms.replace(0, np.nan)).clip(-2, 2).fillna(0.0)
    factor = (1 - 0.5 * scaled_roc) ** 2
    adaptive_period = (base_period * factor).clip(lower=2.0)

    adaptive_ss = _supersmoother_adaptive(close, adaptive_period)

    raw_long = adaptive_ss > fixed_ss

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            want_flat = (not bool(raw_long.iloc[i])) and held >= min_hold_days
            if want_flat or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(raw_long.iloc[i]):
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
