"""Strategy: Wilder Volatility Breakout (SIC/ARC/SAR) trailing-stop-and-reverse
system, adapted long-only -- trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-011):
Per J. Welles Wilder's original "Volatility System" (New Concepts in
Technical Trading Systems, 1978), as specified with the exact formula at
https://oxfordstrat.com/trading-strategies/volatility-breakout/: define
ARC[i] = ATR[i] * Constant (a volatility-scaled breakout distance), and
SIC (Significant Close) as the extreme favorable close price reached while
in a trade. The stop-and-reverse point SAR = SIC -/+ ARC distance. A
breakout beyond the ARC distance from the SIC signals the trend has
resumed/reversed with enough force to warrant a position, while price
inside that band is considered "noise". For the long-only version required
by SAFETY.md: while flat, track a rolling SIC_low anchor (lowest close over
a lookback) and enter long when close breaks above SIC_low + ARC (a
volatility-scaled upside breakout); while long, trail SIC_high = running max
close since entry and exit when close drops below SIC_high - ARC (the
volatility trailing stop), or when a fixed auxiliary ATR-multiple stop-loss
(ATR_length=20, ATR_stop=6, per source's own auxiliary spec) is hit, or a
max_hold_days time-stop. First Wilder Volatility System / SIC-ARC-SAR
strategy in this repo -- distinct from prior ATR-trailing-stop strategies
(Chandelier Exit, Chande Kroll Stop, SuperTrend) since this uses Wilder's
own SIC-anchor-plus-ARC-distance construction (running favorable-close
extreme trailed by a volatility band) rather than a highest-high/ATR or
midline+ATR offset.

Signal logic
------------
- True range / ATR(atr_length) computed Wilder-style (RMA/EWM alpha=1/n).
- ARC = ATR(atr_length) * arc_constant.
- Entry (long, while flat): close > rolling_min(close, lookback).shift(1) + ARC
  (breakout above the recent-low anchor by more than the ARC distance).
- While long: SIC_high = running max(close) since entry;
  trailing_stop = SIC_high - ARC.
  Also track a fixed stop-loss: entry_price - ATR(atr_length)*atr_stop_mult
  (set once at entry, per source's auxiliary spec).
- Exit: close < trailing_stop, OR close < fixed_stop_loss, OR
  max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series   ({0,1} position)
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


def _wilder_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def generate_signals(
    price_df: pd.DataFrame,
    atr_length: int = 20,
    arc_constant: float = 3.0,
    lookback: int = 20,
    atr_stop_mult: float = 6.0,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    atr = _wilder_atr(high, low, close, atr_length)
    arc = atr * arc_constant
    entry_anchor = close.rolling(lookback, min_periods=lookback).min().shift(1)
    entry_trigger = close > (entry_anchor + arc)

    close_arr = close.to_numpy(dtype=float)
    arc_arr = arc.to_numpy(dtype=float)
    atr_arr = atr.to_numpy(dtype=float)
    entry_arr = entry_trigger.fillna(False).to_numpy()

    n = len(df)
    pos_arr = [0] * n

    in_pos = False
    sic_high = np.nan
    fixed_stop = np.nan
    hold_counter = 0

    for i in range(n):
        c = close_arr[i]
        a = arc_arr[i]
        if in_pos:
            hold_counter += 1
            if c > sic_high:
                sic_high = c
            trailing_stop = sic_high - a if not np.isnan(a) else -np.inf
            exit_now = (
                c < trailing_stop
                or (not np.isnan(fixed_stop) and c < fixed_stop)
                or hold_counter >= max_hold_days
            )
            if exit_now:
                in_pos = False
                sic_high = np.nan
                fixed_stop = np.nan
                hold_counter = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if bool(entry_arr[i]) and not np.isnan(a):
                in_pos = True
                sic_high = c
                atr_now = atr_arr[i]
                fixed_stop = c - atr_stop_mult * atr_now if not np.isnan(atr_now) else np.nan
                hold_counter = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    atr_length: int = 20,
    arc_constant: float = 3.0,
    lookback: int = 20,
    atr_stop_mult: float = 6.0,
    max_hold_days: int = 40,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        atr_length=atr_length,
        arc_constant=arc_constant,
        lookback=lookback,
        atr_stop_mult=atr_stop_mult,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
