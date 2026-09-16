"""Strategy: Garman-Klass realized-volatility percentile compression breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-090):
Garman-Klass volatility uses all four OHLC prices (not just close-to-close)
to estimate realized volatility more efficiently, which should let it flag
volatility-regime transitions (compression -> expansion) earlier than a
plain close-based vol measure. Per
https://pinescriptforge.com/strategy/garman-klass-volatility (visited this
iteration): "Enter breakout when GK volatility begins expanding from a low
percentile. Direction based on the first 1x ATR breakout from the
compression range. Exit when GK volatility peaks and begins contracting.
Trail at 1.5x ATR."

Implemented long-only (repo convention) as:
- Garman-Klass variance estimator (per bar):
    GK = 0.5*(ln(H/L))^2 - (2*ln(2)-1)*(ln(C/O))^2
  Rolling mean of GK over `gk_window`, sqrt-annualized -> GK vol series.
- Percentile rank of current GK vol within a trailing `pctile_lookback`
  window. "Compression" = GK vol percentile <= `compression_pctile`
  (source's "low percentile" starting condition).
- Breakout trigger: while in/just-exited compression (within
  `breakout_grace_days` bars of last compression reading), price closes
  above the highest high of the last `gk_window` bars + 1x ATR(atr_window)
  (source's "first 1x ATR breakout from the compression range").
- Exit: GK vol percentile peaks and starts contracting (current reading
  below its own value `decline_confirm_days` bars ago, after having been
  above `compression_pctile`), OR a 1.5x ATR trailing stop from the running
  max close since entry, OR `max_hold_days` time-stop.

First Garman-Klass Volatility entry in this repo (0 prior matches in
strategies_index.jsonl for "Garman-Klass" / "Garman Klass").

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword args (grid_test.py calls
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


def _garman_klass_vol(df: pd.DataFrame, gk_window: int) -> pd.Series:
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    log_hl = np.log(h / l)
    log_co = np.log(c / o)
    gk = 0.5 * (log_hl ** 2) - (2 * np.log(2) - 1) * (log_co ** 2)
    gk = gk.clip(lower=0)  # numerical noise can go slightly negative
    gk_var_roll = gk.rolling(gk_window).mean()
    gk_vol = np.sqrt(gk_var_roll * 252)
    return gk_vol


def _atr(df: pd.DataFrame, atr_window: int) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    prev_close = c.shift(1)
    tr = pd.concat(
        [h - l, (h - prev_close).abs(), (l - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(atr_window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    gk_window: int = 20,
    pctile_lookback: int = 252,
    compression_pctile: float = 0.20,
    atr_window: int = 14,
    atr_mult_entry: float = 1.0,
    atr_mult_stop: float = 1.5,
    breakout_grace_days: int = 5,
    decline_confirm_days: int = 3,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    gk_vol = _garman_klass_vol(df, gk_window)
    gk_pctile = gk_vol.rolling(pctile_lookback, min_periods=gk_window).apply(
        lambda x: (x[-1] > x[:-1]).mean() if len(x) > 1 else np.nan, raw=True
    )
    atr = _atr(df, atr_window)
    range_high = high.rolling(gk_window).max()

    compression = gk_pctile <= compression_pctile
    # in/just-exited compression window: was compressed within last N bars
    recently_compressed = compression.rolling(breakout_grace_days, min_periods=1).max().astype(bool)

    breakout_level = range_high + atr_mult_entry * atr
    entry_signal = recently_compressed.fillna(False) & (close > breakout_level.shift(1))

    # decline confirmation: current pctile below its value N bars ago after
    # having peaked above compression threshold at some point during the hold
    pctile_declining = gk_pctile < gk_pctile.shift(decline_confirm_days)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    running_max_close = 0.0
    saw_expansion = False

    close_vals = close.values
    entry_vals = entry_signal.fillna(False).values
    decline_vals = pctile_declining.fillna(False).values
    pctile_vals = gk_pctile.values
    atr_vals = atr.values

    for i in range(n):
        if in_position:
            held = i - entry_idx
            running_max_close = max(running_max_close, close_vals[i])
            if not saw_expansion and pctile_vals[i] > compression_pctile:
                saw_expansion = True
            stop_price = running_max_close - atr_mult_stop * (atr_vals[i] if not np.isnan(atr_vals[i]) else 0.0)
            hit_stop = close_vals[i] < stop_price
            hit_decline = saw_expansion and bool(decline_vals[i])
            if hit_stop or hit_decline or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_vals[i]):
                in_position = True
                entry_idx = i
                running_max_close = close_vals[i]
                saw_expansion = False
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
