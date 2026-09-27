"""Strategy: Volume-Confirmed Pivot Resistance Breakout long.

Hypothesis (source: https://www.luxalgo.com/library/indicator/support-and-resistance-levels-with-breaks/,
read 2026-09-28 via browser_exec while browsing LuxAlgo's Volume at
Breakout concept implementations after web_search's DDGS backend
repeatedly failed this iteration):

LuxAlgo's "Support and Resistance Levels with Breaks" draws pivot-based S/R
levels (a swing high/low confirmed `right_bars` bars after formation, the
standard fractal-pivot construction) and only TAGS a level break when a
built-in Volume Oscillator confirms the breach: source's own words,
"a built-in Volume Oscillator screens each breach, filtering out
low-participation pokes so the chart highlights breakout volume worth
taking seriously... plenty of levels fail quietly and reverse. By
insisting on volume, the tool keeps your focus on breaks that reflect real
participation."

This is distinct from every prior breakout strategy already tested in this
repo: the closest relative, Bill Williams Fractals (2026-09-04-134), uses
the identical pivot-detection geometry but has NO volume confirmation gate
at all -- it fires on every fractal-high break regardless of participation.
This strategy tests whether adding the source's own volume-oscillator
confirmation (percentage-based fast/slow volume MA divergence, not just a
raw volume-multiple threshold like other volume-gated breakouts in this
repo) meaningfully improves on the un-gated fractal breakout's rejection.

Signal logic (daily-bar mechanical proxy for source's pivot + volume-oscillator
confirmation):
- Pivot high: high[i] is the max of the window [i-left_bars, i+right_bars]
  (confirmed right_bars bars later, no lookahead at signal time since the
  confirmation only becomes known after right_bars have passed).
- Resistance level: the most recently CONFIRMED pivot high price.
- Volume Oscillator: (EMA(volume, vo_fast) - EMA(volume, vo_slow)) /
  EMA(volume, vo_slow) * 100 (standard TradingView Volume Oscillator
  formula, the same "Volume Oscillator" family LuxAlgo's indicator embeds).
- Confirmed breakout: close crosses above the current resistance level AND
  Volume Oscillator on that bar >= `volume_threshold` (percent) -- source's
  own "Volume Threshold" setting.
- Entry: long at close of a confirmed breakout bar (if not already in a
  position).
- Exit: close falls back below the broken resistance level (failed
  breakout / "silent" reversal), OR a max_hold_days time-stop -- whichever
  comes first.

Interface contract (see validation/validators.py and validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _confirmed_pivot_highs(high: pd.Series, left_bars: int, right_bars: int) -> pd.Series:
    """Return a series, indexed like `high`, holding the most recently
    CONFIRMED pivot-high price known as of each bar (NaN before the first
    confirmation). A pivot at index i is confirmed at index i+right_bars."""
    n = len(high)
    high_arr = high.to_numpy()
    confirmed_level = np.full(n, np.nan)

    current_level = np.nan
    for i in range(n):
        # Check if bar (i - right_bars) is a confirmed pivot high today.
        pivot_idx = i - right_bars
        if pivot_idx - left_bars >= 0 and pivot_idx + right_bars < n and pivot_idx >= 0:
            window_start = max(0, pivot_idx - left_bars)
            window_end = min(n, pivot_idx + right_bars + 1)
            if high_arr[pivot_idx] == np.max(high_arr[window_start:window_end]):
                current_level = high_arr[pivot_idx]
        confirmed_level[i] = current_level

    return pd.Series(confirmed_level, index=high.index)


def _volume_oscillator(volume: pd.Series, fast: int, slow: int) -> pd.Series:
    ema_fast = volume.ewm(span=fast, adjust=False).mean()
    ema_slow = volume.ewm(span=slow, adjust=False).mean()
    return (ema_fast - ema_slow) / ema_slow.replace(0.0, np.nan) * 100.0


def generate_signals(
    price_df: pd.DataFrame,
    left_bars: int = 15,
    right_bars: int = 15,
    vo_fast: int = 5,
    vo_slow: int = 10,
    volume_threshold: float = 5.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    volume = df["volume"]

    resistance = _confirmed_pivot_highs(high, left_bars, right_bars)
    vol_osc = _volume_oscillator(volume, vo_fast, vo_slow)

    breakout = (close > resistance) & (close.shift(1) <= resistance.shift(1))
    volume_confirmed = vol_osc >= volume_threshold
    confirmed_breakout = breakout & volume_confirmed

    n = len(df)
    close_arr = close.to_numpy()
    resistance_arr = resistance.to_numpy()
    confirmed_breakout_arr = confirmed_breakout.fillna(False).to_numpy()

    pos = pd.Series(0.0, index=df.index)
    in_pos = False
    hold_count = 0
    stop_level = np.nan

    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = (
                (not np.isnan(stop_level) and close_arr[i] < stop_level)
                or hold_count >= max_hold_days
            )
            if exit_now:
                in_pos = False
                hold_count = 0
                stop_level = np.nan
            else:
                pos.iloc[i] = 1.0

        if not in_pos and bool(confirmed_breakout_arr[i]):
            in_pos = True
            hold_count = 0
            stop_level = resistance_arr[i]
            pos.iloc[i] = 1.0

    return pos


def generate_returns(
    price_df: pd.DataFrame,
    left_bars: int = 15,
    right_bars: int = 15,
    vo_fast: int = 5,
    vo_slow: int = 10,
    volume_threshold: float = 5.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    pos = generate_signals(
        df,
        left_bars=left_bars,
        right_bars=right_bars,
        vo_fast=vo_fast,
        vo_slow=vo_slow,
        volume_threshold=volume_threshold,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0.0)
    return strat_ret
