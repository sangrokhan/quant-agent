"""Strategy: Value Area Reclaim, confirmed by Bullish Engulfing + Volume
Expansion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-063):
Direct rescue attempt for near-miss/rejected 2026-09-10-001 (rolling
Volume-Profile Value-Area reclaim: long when yesterday's close was below
VAL and today's close reclaims back above VAL). That entry decisively
failed Sharpe (0.016) and TC-survival, with 102 trades -- suggesting too
many low-quality/fakeout reclaims were being traded. Per LuxAlgo's "Value
Area Reversion Signals" indicator page
(https://www.luxalgo.com/library/indicator/value-area-reversion-signals/):
"A bullish reclaim signal occurs when the price drops below the Value
Area Low, struggles to maintain momentum, and then produces a BULLISH
ENGULFING candle that re-enters the Value Area WITH EXPANDING VOLUME...
these signals require specific volume expansion conditions [that] act as
a filter against fakeouts." This iteration adds exactly those two
source-mandated confirmation filters (bullish engulfing candle pattern +
volume expansion vs. a trailing average) on top of the existing VAL
reclaim logic, directly targeting the prior rejection's likely cause
(unfiltered fakeout reclaims).

Signal logic
------------
- Rolling N-day (profile_window) volume profile of daily HLC3, split into
  `n_bins` price bins; POC = highest-volume bin midpoint; Value Area
  (VAL/VAH) = narrowest contiguous bin range containing va_pct of total
  volume, expanding outward from POC (same construction as
  2026-09-04-150/2026-09-08-129/2026-09-10-001).
- Bullish engulfing candle: today's body (open..close) fully engulfs
  yesterday's body, AND today's candle is bullish (close > open) while
  yesterday's was bearish (close < open).
- Volume expansion: today's volume > vol_expansion_mult * rolling
  vol_avg_window-day average volume.
- Entry (long): yesterday's close < VAL(t-1) AND today's close >= VAL(t)
  (reclaim) AND today is a bullish engulfing candle AND volume expansion
  confirms.
- Exit: close reaches POC (target), OR close falls back below VAL (failed
  reclaim), OR a max_hold_days time-stop.
- Flat otherwise; long-only.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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


def _rolling_value_area(
    df: pd.DataFrame, profile_window: int, n_bins: int, va_pct: float
):
    """Return (poc, val, vah) series, each computed from a trailing
    profile_window-day rolling volume histogram of HLC3."""
    hlc3 = (df["high"] + df["low"] + df["close"]) / 3.0
    volume = df["volume"]

    poc = pd.Series(index=df.index, dtype=float)
    val = pd.Series(index=df.index, dtype=float)
    vah = pd.Series(index=df.index, dtype=float)

    for i in range(len(df)):
        if i < profile_window:
            continue
        window_price = hlc3.iloc[i - profile_window : i]
        window_vol = volume.iloc[i - profile_window : i]
        lo, hi = window_price.min(), window_price.max()
        if hi <= lo:
            continue
        bins = np.linspace(lo, hi, n_bins + 1)
        bin_idx = np.clip(np.digitize(window_price.values, bins) - 1, 0, n_bins - 1)
        hist = np.zeros(n_bins)
        for b, v in zip(bin_idx, window_vol.values):
            hist[b] += v
        total_vol = hist.sum()
        if total_vol <= 0:
            continue
        poc_bin = int(np.argmax(hist))
        bin_centers = (bins[:-1] + bins[1:]) / 2.0
        poc.iloc[i] = bin_centers[poc_bin]

        included = {poc_bin}
        acc_vol = hist[poc_bin]
        lo_b, hi_b = poc_bin, poc_bin
        while acc_vol < va_pct * total_vol and (lo_b > 0 or hi_b < n_bins - 1):
            below = hist[lo_b - 1] if lo_b > 0 else -1
            above = hist[hi_b + 1] if hi_b < n_bins - 1 else -1
            if above >= below:
                hi_b += 1
                acc_vol += hist[hi_b]
                included.add(hi_b)
            else:
                lo_b -= 1
                acc_vol += hist[lo_b]
                included.add(lo_b)
        val.iloc[i] = bin_centers[lo_b]
        vah.iloc[i] = bin_centers[hi_b]

    return poc, val, vah


def generate_signals(
    price_df: pd.DataFrame,
    profile_window: int = 20,
    n_bins: int = 20,
    va_pct: float = 0.70,
    vol_avg_window: int = 20,
    vol_expansion_mult: float = 1.3,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    volume = df["volume"]

    poc, val, vah = _rolling_value_area(df, profile_window, n_bins, va_pct)

    below_val_prev = (close.shift(1) < val.shift(1)).fillna(False)
    reclaimed_val = (close >= val).fillna(False)

    bullish_engulfing = (
        (close > open_)
        & (close.shift(1) < open_.shift(1))
        & (close >= open_.shift(1))
        & (open_ <= close.shift(1))
    ).fillna(False)

    vol_avg = volume.rolling(vol_avg_window).mean()
    volume_expansion = (volume > vol_expansion_mult * vol_avg).fillna(False)

    entry = below_val_prev & reclaimed_val & bullish_engulfing & volume_expansion
    exit_target = (close >= poc).fillna(False)
    exit_failed = (close < val).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_target.iloc[i]) or bool(exit_failed.iloc[i]) or held >= max_hold_days:
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
