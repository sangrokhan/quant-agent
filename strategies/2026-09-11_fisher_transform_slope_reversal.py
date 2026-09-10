"""Strategy: Fisher Transform slope-reversal entry, gated by 50-period SMA trend.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-001),
sourced from https://www.daytrading.com/fisher-transform (visited this
iteration): the site's own worked S&P 500 example gives an explicit rule
set distinct from the signal-line-crossover variants already tested in
this repo (2026-09-04-051 rejected plain extreme-threshold crossover;
2026-09-05-086 rejected signal-line-crossover + trend filter):

    Long trades:
    - Fisher Transform must be NEGATIVE (price "stretched"/oversold)
    - Entry triggered on a SLOPE REVERSAL of the Fisher line itself
      (from negatively-sloped to positively-sloped), NOT a crossover
      against a separate signal/trigger line.
    - Source's own finding: trading this in isolation "doesn't work that
      well" (4 winners / 4 losers, roughly breakeven), but restricting
      trades to the direction of the prevailing trend (a 50-period moving
      average) "we see greater accuracy" (3 winners / 1 loser in the
      worked example).

This is mechanically distinct from prior Fisher Transform variants in
this repo: no separate trigger/signal line is used at all -- the entry
condition is the Fisher line's own local minimum (slope flips from <=0 to
>0) while the line is still in negative/oversold territory, gated by the
same close>SMA(trend_window) trend filter used elsewhere in this repo
(e.g. IMI 2026-09-05-071, BB mean-reversion 2026-09-03-001).

Signal logic
------------
- Fisher Transform: normalize close over `fisher_window` bars to [-1, 1]
  via the rolling min/max midpoint method, apply the Ehlers Fisher
  transform 0.5*ln((1+x)/(1-x)).
- Long entry: Fisher's 1-bar slope flips from non-positive to positive
  (local trough) while Fisher < 0 (oversold zone, source's own "must be
  negative" condition) AND close > SMA(trend_window) (source's trend
  filter).
- Exit to flat: Fisher's slope flips back down (from positive to
  non-positive, i.e. a fresh local peak), OR close drops below the trend
  SMA (risk-off exit), OR after `max_hold_days` bars.
- Long-only (no shorts), consistent with this repo's other strategies and
  SAFETY.md scope.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, position lagged by 1 day to avoid look-ahead bias)
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


def _fisher_transform(close: pd.Series, window: int) -> pd.Series:
    roll_max = close.rolling(window, min_periods=window).max()
    roll_min = close.rolling(window, min_periods=window).min()
    rng = (roll_max - roll_min).replace(0, np.nan)

    raw = 2.0 * ((close - roll_min) / rng - 0.5)
    raw = raw.clip(-0.999, 0.999)

    fisher = 0.5 * np.log((1 + raw) / (1 - raw))
    return fisher


def generate_signals(
    price_df: pd.DataFrame,
    fisher_window: int = 9,
    trend_window: int = 50,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fisher = _fisher_transform(close, fisher_window)
    fisher_diff = fisher.diff()

    sma_trend = close.rolling(trend_window, min_periods=trend_window).mean()
    above_trend = (close > sma_trend).fillna(False)

    # Slope flips from non-positive to positive == local trough.
    slope_up_flip = (fisher_diff > 0) & (fisher_diff.shift(1) <= 0)
    # Slope flips from non-negative to negative == local peak.
    slope_down_flip = (fisher_diff < 0) & (fisher_diff.shift(1) >= 0)

    entry_event = (
        slope_up_flip.fillna(False)
        & (fisher < 0).fillna(False)
        & above_trend
    )
    exit_event = slope_down_flip.fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0
    entry_arr = entry_event.values
    exit_arr = exit_event.values
    above_trend_arr = above_trend.values

    for i in range(len(df.index)):
        if in_position:
            hold_count += 1
            if exit_arr[i] or (not above_trend_arr[i]) or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_arr[i]:
                in_position = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **params)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
