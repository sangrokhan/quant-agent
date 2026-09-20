"""Strategy: Price "jerk" (3rd derivative of smoothed log price) shock signal,
gated by a 200-day trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-205):
Source: https://www.tradingview.com/script/eUZZ1SMw-Shock-Detector-Price-Jerk-with-Std-Dev-Bands/
("Shock Detector: Price Jerk with Std-Dev Bands", tmfou, TradingView,
Aug 2025). The source describes "jerk" as the third time-derivative of
(smoothed, log) price -- the rate of change of price acceleration -- and
proposes using standard-deviation bands around it to flag statistically
unusual "shock" moves, suggesting combination with a trend filter for early
breakout/reversal signals. This repo has tested velocity (ROC/momentum) and
acceleration (2nd-derivative) indicators extensively but no jerk (3rd
derivative) variant yet.

Concrete rule (this iteration's operationalization of the source's general
idea, not literally implemented in the source -- the source only describes
the indicator, not a full trading rule):
- Smooth log(close) with an EMA (`smooth_window`) to reduce noise.
- velocity = diff(smoothed log price); acceleration = diff(velocity);
  jerk = diff(acceleration) (finite-difference 3rd derivative).
- z-score jerk over a rolling window (`z_window`) -> "shock" when
  |z| >= `shock_z`.
- Entry (long): a positive jerk shock (z >= shock_z, i.e. a sudden upward
  acceleration-of-acceleration) occurs AND price is above its 200-day SMA
  (uptrend gate -- avoids buying "shocks" that are really trend-ending
  crash/whipsaw noise in a downtrend, consistent with prior findings in
  this repo that most raw oscillator-threshold signals need a trend filter
  to survive validation, e.g. cci_trend_continuation, rsi2_meanrev_trend200).
- Exit: jerk z-score reverts back inside the band (|z| < exit_z, a lower
  threshold than entry for hysteresis) OR trend gate flips (close < SMA200)
  OR after `max_hold_days` trading days.
- Flat otherwise.

Interface contract (validation/grid_test.py, validation/validators.py):
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


def generate_signals(
    price_df: pd.DataFrame,
    smooth_window: int = 5,
    z_window: int = 60,
    shock_z: float = 2.0,
    exit_z: float = 0.5,
    trend_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    log_close = close.apply(lambda x: math.log(x) if x and x > 0 else None).astype(float)
    smoothed = log_close.ewm(span=smooth_window, adjust=False).mean()

    velocity = smoothed.diff()
    acceleration = velocity.diff()
    jerk = acceleration.diff()

    jerk_mean = jerk.rolling(z_window).mean()
    jerk_std = jerk.rolling(z_window).std()
    jerk_z = (jerk - jerk_mean) / jerk_std.replace(0, np.nan)

    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    entry = (jerk_z >= shock_z) & uptrend.fillna(False)
    exit_shock_fade = jerk_z.abs() < exit_z
    exit_trend_flip = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            fade = bool(exit_shock_fade.iloc[i]) if not pd.isna(exit_shock_fade.iloc[i]) else False
            flip = bool(exit_trend_flip.iloc[i]) if not pd.isna(exit_trend_flip.iloc[i]) else False
            if fade or flip or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]) if not pd.isna(entry.iloc[i]) else False:
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
