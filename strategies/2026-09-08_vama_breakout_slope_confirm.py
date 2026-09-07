"""Strategy: Volatility Adjusted Moving Average (VAMA) breakout + slope confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per the Volatility Adjusted Moving Average (VAMA), transcribed at
https://pineify.app/resources/blog/volatility-adjusted-moving-average-indicator-tradingview-pine-script :
VAMA scales a baseline EMA by a volatility ratio derived from the recent
High-Low range relative to that same EMA: VolRatio = (HighestHigh(lookback)
- LowestLow(lookback)) / EMA(close, length); VAMA = EMA(close, length) *
(1 + VolRatio * sensitivity_factor). The source's stated entry rule:
"Strong Long Entry: Price breaks above VAMA while VAMA slopes upward"
(with the "confirmation trick" of waiting for VAMA's slope to turn
positive before entering); exit when "Price starts staying on the wrong
side of VAMA" (trend change) or "VAMA starts flattening out" (momentum
loss), plus a max_hold_days time-stop as this repo's standard safety net.

First VAMA strategy in this repo -- distinct from other adaptive moving
averages already tested (KAMA: efficiency-ratio-scaled smoothing constant;
FRAMA: fractal-dimension-scaled; MAMA/FAMA: Hilbert-cycle-period-scaled)
since VAMA's adaptation mechanism scales a plain EMA multiplicatively by a
High-Low-range-relative-to-EMA volatility ratio, a genuinely different
construction from efficiency-ratio, fractal-dimension, or cycle-period
adaptivity.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  (0/1 long/flat)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _vama(high: pd.Series, low: pd.Series, close: pd.Series, length: int, vol_lookback: int, sensitivity_factor: float) -> pd.Series:
    ema = close.ewm(span=length, adjust=False).mean()
    highest_high = high.rolling(vol_lookback).max()
    lowest_low = low.rolling(vol_lookback).min()
    vol_ratio = (highest_high - lowest_low) / ema
    vama = ema * (1 + vol_ratio * sensitivity_factor)
    return vama


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 14,
    vol_lookback: int = 10,
    sensitivity_factor: float = 1.0,
    slope_window: int = 3,
    flatten_threshold: float = 0.0005,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    vama = _vama(high, low, close, length, vol_lookback, sensitivity_factor)
    vama_slope = vama.diff(slope_window) / slope_window
    vama_slope_pct = vama_slope / vama

    price_above = close > vama
    slope_up = vama_slope > 0
    flattening = vama_slope_pct.abs() < flatten_threshold

    cross_up = price_above & (~price_above.shift(1).fillna(False))
    entry = cross_up & slope_up.shift(1).fillna(False)

    exit_wrong_side = ~price_above
    exit_signal = exit_wrong_side | flattening

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
