"""Strategy: Volume Profile POC / Value-Area mean reversion (rolling daily
approximation).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-150):
Volume Profile shows where volume traded at each price over a lookback
window; the Point of Control (POC, the highest-volume price) acts as a
"magnet" price repeatedly returns to, and the Value Area (VA, price band
containing ~70% of volume, bounded by VAH/VAL) marks the "fair value"
range. Per QuantCrawler's explainer, the classic mean-reversion setup is:
enter when price reaches a value-area extreme (VAH short / VAL long),
target the POC, stop beyond the VA boundary. This strategy approximates
Volume Profile using a rolling N-day volume-weighted histogram of daily
typical price (HLC3) weighted by that day's volume (since intraday
tick-level volume-at-price data isn't available via data/loaders.py):
POC = the histogram bin with the most accumulated volume; VA = the
narrowest contiguous price band (built by adding bins outward from POC)
containing >= 70% of the rolling window's volume. Long entry when close
drops to/below VAL (discount zone); exit when close reaches/crosses the
POC (mean-reversion target) or drops further below a stop level (VAL minus
an ATR buffer, protecting against a trending breakdown), or a
max_hold_days time-stop. First Volume-Profile-family strategy in this
repo.

Signal logic
------------
- Rolling window of `profile_window` daily bars.
- Each bar's "typical price" = HLC3, weighted by that bar's volume.
- Build `n_bins` equal-width price bins spanning the rolling window's
  high/low range; accumulate volume per bin.
- POC = bin with max accumulated volume (bin midpoint).
- VA = expand outward from the POC bin (alternating up/down, whichever
  neighboring bin has more volume) until >= value_area_pct of total
  volume is captured; VAL/VAH = min/max price edge of the captured bins.
- Entry (long): close <= VAL.
- Exit: close >= POC, OR close <= VAL - atr_mult * ATR (stop-out), OR
  max_hold_days elapsed.
- Flat otherwise.
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def _profile_levels(
    window_df: pd.DataFrame, n_bins: int, value_area_pct: float
) -> tuple[float, float, float]:
    """Returns (poc, val, vah) for one rolling window slice."""
    typical = (window_df["high"] + window_df["low"] + window_df["close"]) / 3.0
    vol = window_df["volume"].to_numpy()
    lo, hi = window_df["low"].min(), window_df["high"].max()
    if hi <= lo or vol.sum() <= 0:
        mid = (hi + lo) / 2.0
        return mid, mid, mid

    edges = np.linspace(lo, hi, n_bins + 1)
    bin_idx = np.clip(np.digitize(typical.to_numpy(), edges) - 1, 0, n_bins - 1)
    bin_vol = np.zeros(n_bins)
    for idx, v in zip(bin_idx, vol):
        bin_vol[idx] += v

    poc_bin = int(np.argmax(bin_vol))
    poc_price = (edges[poc_bin] + edges[poc_bin + 1]) / 2.0

    total_vol = bin_vol.sum()
    target = value_area_pct * total_vol
    captured = bin_vol[poc_bin]
    lo_bin, hi_bin = poc_bin, poc_bin
    while captured < target and (lo_bin > 0 or hi_bin < n_bins - 1):
        vol_below = bin_vol[lo_bin - 1] if lo_bin > 0 else -1
        vol_above = bin_vol[hi_bin + 1] if hi_bin < n_bins - 1 else -1
        if vol_above >= vol_below:
            hi_bin += 1
            captured += bin_vol[hi_bin]
        else:
            lo_bin -= 1
            captured += bin_vol[lo_bin]

    val_price = edges[lo_bin]
    vah_price = edges[hi_bin + 1]
    return poc_price, val_price, vah_price


def generate_signals(
    price_df: pd.DataFrame,
    profile_window: int = 40,
    n_bins: int = 20,
    value_area_pct: float = 0.70,
    atr_window: int = 14,
    atr_mult: float = 1.5,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    atr = _atr(df, atr_window)

    poc_list, val_list = [np.nan] * len(df), [np.nan] * len(df)
    for i in range(profile_window, len(df)):
        window_df = df.iloc[i - profile_window : i]
        poc, val, vah = _profile_levels(window_df, n_bins, value_area_pct)
        poc_list[i] = poc
        val_list[i] = val

    poc_s = pd.Series(poc_list, index=df.index)
    val_s = pd.Series(val_list, index=df.index)
    close = df["close"]

    entry_raw = (close <= val_s).fillna(False).to_numpy()
    exit_target = (close >= poc_s).fillna(False)
    exit_stop = (close <= (val_s - atr_mult * atr)).fillna(False)
    exit_raw = (exit_target | exit_stop).fillna(True).to_numpy()

    pos_arr = [0] * len(df)
    in_pos = False
    hold_days = 0
    for i in range(len(df)):
        if in_pos:
            hold_days += 1
            if exit_raw[i] or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_raw[i]:
                in_pos = True
                hold_days = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    profile_window: int = 40,
    n_bins: int = 20,
    value_area_pct: float = 0.70,
    atr_window: int = 14,
    atr_mult: float = 1.5,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        profile_window=profile_window,
        n_bins=n_bins,
        value_area_pct=value_area_pct,
        atr_window=atr_window,
        atr_mult=atr_mult,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
