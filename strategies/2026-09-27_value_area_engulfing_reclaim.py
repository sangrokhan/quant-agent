"""Strategy: Volume-Profile Value-Area engulfing-candle reclaim reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl, id TBD):
Per LuxAlgo's "Value Area Reversion Signals" indicator
(https://www.luxalgo.com/library/indicator/value-area-reversion-signals,
published Aug 18 2026, read via browser_exec this iteration -- web_search
DDGS backend was flaky for freshest-source discovery so LuxAlgo's
newest-sorted library listing was browsed directly): a rolling N-day
volume profile has a Point of Control (POC, highest-volume price) and a
Value Area (VA, narrowest band around POC holding value_area_pct of total
volume, bounded by VAL/VAH). The source's disclosed rule: a "bullish
reclaim" signal fires when price breaks/closes BELOW VAL, then on a
subsequent bar produces a bullish ENGULFING candle (close > prior open,
open < prior close, full-range engulf) that closes back INSIDE the Value
Area, with volume expansion (today's volume >= vol_mult x its trailing
average) -- interpreted as a failed breakdown being aggressively
overwhelmed by buyers, i.e. the breakout was a fakeout and price should
travel back toward POC/VAH. Symmetric bearish version for shorts (breakout
above VAH, failed, bearish engulfing candle re-enters VA with volume, short
back toward POC/VAL) is implemented but this repo tests LONG-ONLY here to
keep scope tight (short leg parked for a future iteration).

This is distinct from the earlier-tested plain VAL-reclaim entry
(2026-09-10-001, id "2026-09-10-001": "long entry when yesterday's close
was below VAL and today's close reclaims back above VAL", exit at POC target)
in two ways: (1) requires an actual bullish ENGULFING CANDLE pattern on the
reclaim bar, not just any close-above-VAL bar, and (2) requires a volume
EXPANSION filter on that reclaim bar -- both meant to filter out weak,
low-conviction reclaims that the plain version could not distinguish.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
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
    df: pd.DataFrame,
    lookback: int,
    n_bins: int,
    value_area_pct: float,
):
    """Compute rolling POC/VAL/VAH from a volume-weighted HLC3 histogram.

    Vectorised-ish but done per-bar (acceptable for daily-bar backtests of
    a few thousand rows): for each bar i, build a volume histogram of the
    trailing `lookback` bars' HLC3 prices, find the POC bin, then expand
    outward (higher-volume-neighbor-first, matching LuxAlgo/standard Market
    Profile convention) until >= value_area_pct of total volume is
    captured. VAL/VAH are the low/high edges of the captured bin range.
    """
    close = df["close"]
    high = df["high"]
    low = df["low"]
    vol = df["volume"].fillna(0.0)
    hlc3 = (high + low + close) / 3.0

    n = len(df)
    poc = np.full(n, np.nan)
    val = np.full(n, np.nan)
    vah = np.full(n, np.nan)

    hlc3_vals = hlc3.values
    vol_vals = vol.values

    for i in range(lookback, n):
        window_price = hlc3_vals[i - lookback : i]
        window_vol = vol_vals[i - lookback : i]
        if window_vol.sum() <= 0 or np.all(np.isnan(window_price)):
            continue
        lo, hi = np.nanmin(window_price), np.nanmax(window_price)
        if hi <= lo:
            continue
        bins = np.linspace(lo, hi, n_bins + 1)
        bin_idx = np.clip(np.digitize(window_price, bins) - 1, 0, n_bins - 1)
        hist = np.zeros(n_bins)
        for b, v in zip(bin_idx, window_vol):
            hist[b] += v
        total = hist.sum()
        if total <= 0:
            continue
        poc_bin = int(np.argmax(hist))
        lo_b = hi_b = poc_bin
        captured = hist[poc_bin]
        target = value_area_pct * total
        while captured < target and (lo_b > 0 or hi_b < n_bins - 1):
            left_vol = hist[lo_b - 1] if lo_b > 0 else -1
            right_vol = hist[hi_b + 1] if hi_b < n_bins - 1 else -1
            if right_vol >= left_vol:
                hi_b += 1
                captured += hist[hi_b]
            else:
                lo_b -= 1
                captured += hist[lo_b]
        bin_centers = (bins[:-1] + bins[1:]) / 2.0
        poc[i] = bin_centers[poc_bin]
        val[i] = bins[lo_b]
        vah[i] = bins[hi_b + 1]

    return (
        pd.Series(poc, index=df.index),
        pd.Series(val, index=df.index),
        pd.Series(vah, index=df.index),
    )


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 20,
    n_bins: int = 24,
    value_area_pct: float = 0.70,
    vol_mult: float = 1.3,
    vol_avg_window: int = 20,
    max_hold_days: int = 8,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    volume = df["volume"].fillna(0.0)

    poc, val, vah = _rolling_value_area(df, lookback, n_bins, value_area_pct)

    below_val_prev = close.shift(1) < val.shift(1)
    bullish_engulf = (close > open_.shift(1)) & (open_ < close.shift(1)) & (close > open_)
    avg_vol = volume.rolling(vol_avg_window).mean()
    vol_expand = volume >= (vol_mult * avg_vol)
    reclaims_inside_va = (close >= val) & (close <= vah)

    entry = below_val_prev & bullish_engulf & vol_expand & reclaims_inside_va
    entry = entry.fillna(False)

    exit_target = close >= poc

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            hit_target = bool(exit_target.iloc[i]) if not pd.isna(exit_target.iloc[i]) else False
            if hit_target or held >= max_hold_days:
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
