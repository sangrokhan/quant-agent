"""Strategy: Bulkowski Rounding Bottom breakout (long-only continuation).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/roundb.html (Thomas Bulkowski's
"Encyclopedia of Chart Patterns" stats page; read via browser_exec after
web_search's DDGS backend returned unrelated/garbage results this
iteration). Source's own disclosed statistics and identification rules:

    "Rounding Bottom: Important Bull Market Results: Overall performance
    rank (1 is best): 7 out of 39. Break even failure rate: 4%. Average
    rise: 48%. Throwback rate: 64%. Percentage meeting price target: 65%.
    ... Price trend: Price trends upward to the pattern 67% of the time
    (that is, 67% act as continuation patterns). Shape: Look for a
    rounded bowl shape, usually over many months and usually after an
    upward price trend. ... Confirmation: I use a close above the left
    peak because price on the right might not pause at a minor high. ...
    The Measure Rule: Compute the height from the left saucer lip to the
    lowest valley in the pattern then multiply it by the above
    'percentage meeting price target.' Add the difference to the right
    saucer lip to get a price target."

A break-even failure rate of only 4% is one of the strongest (lowest
failure) statistics of any Bulkowski pattern this repo has sourced so far
-- a materially stronger prior than the Rectangle Top (15%) and Three
Rising Valleys patterns already tested and accepted this cron trigger.
First "Rounding Bottom"/"Rounded Bottom" entry in this repo (0 prior index
hits) -- distinct from every prior pattern tested: it requires a smooth,
gradual U-shaped price decline-then-recovery (not a sharp V-shaped swing
low, not parallel/converging trendlines).

Signal logic (numeric proxy for the source's qualitative "bowl shape")
------------------------------------------------------------------------
1. Bowl detection: over a rolling `bowl_window`-bar lookback, find the
   bar-index of the minimum close (the "lowest valley," per source). A
   valid rounding-bottom candidate requires that minimum to fall roughly
   in the MIDDLE of the window (within `center_tolerance` of the window's
   midpoint, a numeric proxy for "gentle turn" symmetry rather than a
   sharp one-sided drop) -- this discourages simple V-shaped dips from
   qualifying.
2. Left lip: the close at the start of the bowl window (`left_lip`).
   Confirmation point = left_lip (source's own rule: "I use a close above
   the left peak").
3. Prior uptrend filter: close at the start of the bowl window is above
   its own SMA(trend_lookback) (source: "usually after an upward price
   trend").
4. Entry: long the first bar after the valley where close closes above
   `left_lip` (confirmation).
5. Exit: source's own Measure Rule (height = left_lip - valley_price,
   target = left_lip + height * target_pct, source's own disclosed 65%
   "percentage meeting price target"), OR close falling back below the
   valley price (failed breakout), OR a max_hold_days time-stop,
   whichever comes first.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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


def generate_signals(
    price_df: pd.DataFrame,
    bowl_window: int = 60,
    center_tolerance: float = 0.30,
    trend_lookback: int = 50,
    target_pct: float = 0.65,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    close_arr = close.to_numpy()
    n = len(close_arr)

    sma_trend = close.rolling(trend_lookback).mean()
    sma_arr = sma_trend.to_numpy()

    entries = np.zeros(n, dtype=bool)
    left_lips = np.full(n, np.nan)
    valley_prices = np.full(n, np.nan)

    mid_tol = center_tolerance * bowl_window

    for i in range(bowl_window, n):
        window = close_arr[i - bowl_window: i]
        valley_offset = int(np.argmin(window))
        valley_price = window[valley_offset]
        # require valley roughly centered in the window (bowl shape, not a
        # sharp one-sided V near either edge).
        mid = bowl_window / 2.0
        if abs(valley_offset - mid) > mid_tol:
            continue
        left_lip = window[0]
        left_lip_bar = i - bowl_window
        if np.isnan(sma_arr[left_lip_bar]) or close_arr[left_lip_bar] <= sma_arr[left_lip_bar]:
            continue  # prior uptrend filter failed
        # Confirmation: current bar i closes above left_lip, and the
        # valley must have already occurred (valley_offset < bowl_window - 1).
        if valley_offset < bowl_window - 1 and close_arr[i] > left_lip:
            entries[i] = True
            left_lips[i] = left_lip
            valley_prices[i] = valley_price

    position = np.zeros(n, dtype=int)
    in_pos = False
    entry_bar = -1
    entry_lip = np.nan
    entry_valley = np.nan
    target_price = np.nan

    for t in range(n):
        if entries[t] and not in_pos:
            in_pos = True
            entry_bar = t
            entry_lip = left_lips[t]
            entry_valley = valley_prices[t]
            height = entry_lip - entry_valley
            target_price = entry_lip + height * target_pct if height > 0 else np.inf
        if in_pos:
            position[t] = 1
            held = t - entry_bar
            failed = close_arr[t] < entry_valley
            hit_target = close_arr[t] >= target_price
            if failed or hit_target or held >= max_hold_days:
                in_pos = False

    return pd.Series(position, index=close.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
