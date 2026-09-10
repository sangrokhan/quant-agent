"""Strategy: Chop Zone (34-period EMA angle) trend-continuation gated by ADX.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-XXX):
Per https://pineify.app/pine-script/indicators/chop-zone (Pineify engineering
team's Chop Zone indicator, published 2024 -- a Fibonacci 34-period EMA
"angle" trend-strength visualizer): the EMA slope, normalized against the
recent highest-high/lowest-low range and converted to a degree angle via
arccos(1/sqrt(1+dy^2))*180/pi, tells you whether the trend's EMA is
accelerating (steep angle, source's "turquoise"/"dark green" colors, angle
>= angle_strong_threshold) or flat/choppy (source's "yellow", angle near 0).
The source's own disclosed "Strategy 1 -- Trend Continuation with ADX Filter"
combines this with ADX(14): only go long when ADX confirms the move is
directional (adx > adx_threshold) AND the Chop Zone angle has been >=
angle_strong_threshold for angle_confirm_bars consecutive bars (source
default: 2+ bars). Exit when the angle decelerates back down past
angle_exit_threshold (source: "shifts two or more zones toward yellow").
This is the first EMA-slope/angle-trigonometry-based indicator tested in
this repo -- distinct from every prior linear-regression-slope, ADX-alone,
or plain EMA-crossover strategy since Chop Zone's angle transform is a
nonlinear (arccos) normalization of the EMA's *rate of change* relative to
the recent trading range, not a raw slope or price/MA relationship.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Both accept keyword-arg tunable parameters per RESEARCH_LOOP.md Step 5.
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


def _chop_zone_angle(df: pd.DataFrame, ema_len: int, lookback: int, calib: float = 25.0) -> pd.Series:
    """Chop Zone EMA-angle series in degrees (signed: + = rising, - = falling).

    Formula per source: span = calib / (highestHigh - lowestLow) * lowestLow;
    dy = (EMA[t-1] - EMA[t]) / hlc3[t] * span; angle = arccos(1/sqrt(1+dy^2)) * 180/pi.
    Note the source's raw dy sign convention (EMA[t-1]-EMA[t]) is inverted vs
    "rising EMA = positive angle" -- we flip the sign so positive angle means
    an accelerating UP-slope, matching the source's stated color semantics
    (turquoise/positive = bullish).
    """
    close = df["close"]
    high = df["high"]
    low = df["low"]
    hlc3 = (df["high"] + df["low"] + df["close"]) / 3.0

    ema = close.ewm(span=ema_len, adjust=False).mean()
    highest_high = high.rolling(lookback).max()
    lowest_low = low.rolling(lookback).min()
    rng = (highest_high - lowest_low).replace(0, np.nan)

    span = calib / rng * lowest_low
    dy = (ema - ema.shift(1)) / hlc3.replace(0, np.nan) * span  # flipped sign vs source's raw formula
    angle_rad = np.arccos(1.0 / np.sqrt(1.0 + dy ** 2))
    angle_deg = angle_rad * 180.0 / math.pi
    signed_angle = angle_deg * np.sign(dy.fillna(0.0))
    return signed_angle


def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1.0 / period, adjust=False).mean()
    plus_di = 100.0 * pd.Series(plus_dm, index=df.index).ewm(alpha=1.0 / period, adjust=False).mean() / atr.replace(0, np.nan)
    minus_di = 100.0 * pd.Series(minus_dm, index=df.index).ewm(alpha=1.0 / period, adjust=False).mean() / atr.replace(0, np.nan)

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1.0 / period, adjust=False).mean()
    return adx.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    ema_len: int = 34,
    lookback: int = 30,
    adx_period: int = 14,
    adx_threshold: float = 25.0,
    angle_strong_threshold: float = 5.0,
    angle_confirm_bars: int = 2,
    angle_exit_threshold: float = 1.5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    angle = _chop_zone_angle(df, ema_len=ema_len, lookback=lookback)
    adx = _adx(df, period=adx_period)

    strong_up = angle >= angle_strong_threshold
    strong_up_confirmed = strong_up.rolling(angle_confirm_bars).sum() >= angle_confirm_bars
    trend_ok = adx > adx_threshold

    entry = (strong_up_confirmed & trend_ok).fillna(False)
    exit_decel = (angle < angle_exit_threshold).fillna(True)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_decel.iloc[i]) or held >= max_hold_days:
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
