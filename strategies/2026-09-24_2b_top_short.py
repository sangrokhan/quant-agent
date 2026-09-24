"""Strategy: Bulkowski/Sperandeo 2B Top pattern (short-only reversal).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/2B.html (Thomas Bulkowski,
browser_exec fallback -- web_search's DDGS backend cannot extract this
domain). Original rule per Victor Sperandeo (Trader Vic--Methods of a Wall
Street Master), quoted verbatim by the source:

    "In an uptrend, if a higher high is made but fails to carry through,
    and then prices drop below the previous high, then the trend is apt
    to reverse... I prefer to think of a 2B top as one in which price
    begins to form a double top... price exceeds the level of the first
    top and then reverses."

Bulkowski's own large-sample (41,702 samples, 468 stocks, 2010-2020)
research disclosed a precise numeric result table: when the second peak
(C) exceeds the first peak (B) by 0-1%, price drops a median/average of
~10% from the second peak's high to the ultimate low; overall median drop
across all samples is 7-10%. This gives a genuinely novel, precisely
disclosed numeric SHORT-side hypothesis distinct from every other
pattern/indicator strategy tested in this repo (0 prior "2B"/Sperandeo
index hits).

This is a backtested SHORT position (simulated in the returns series via
a {-1,0} position sign, exactly like this cron trigger's earlier
2026-09-24_busted_hs_bottom_short.py) -- not a live order-placement
function, consistent with SAFETY.md (which only prohibits real
order-placement code, not simulated short positions in a backtest).

Signal logic (numeric proxy for the source's qualitative "peak B, peak C
slightly above B, then reversal" 2B Top rule)
------------------------------------------------------------------------
1. Swing pivot detection: same rolling-window fractal test used elsewhere
   in this repo to find swing highs (peaks) over `pivot_window`.
2. For each pair of consecutive swing highs (B at index b, C at index c,
   b < c, with no other swing high strictly between them -- i.e.
   consecutive in the alternating-swing sense): the "2B condition" is
   peak C's high exceeds peak B's high by between 0% and
   `max_peak_excess_pct` (source's own disclosed "I limited the peak-to-
   peak price difference to 5%" -- default 0.05, i.e. "first peak below
   second" by a SMALL margin, not a large breakout).
3. Uptrend precondition (source: "In an uptrend..."): close at peak B is
   above its own SMA(trend_lookback).
4. Entry (SHORT): the first bar after peak C where close falls back below
   peak B's own high level (source's own "then prices drop below the
   previous high" reversal-confirmation trigger).
5. Exit: source's own disclosed target -- price target_pct (default 0.10,
   source's own disclosed median/overall drop) measured down from peak
   C's high, OR close recovers back above peak C's high (stop-loss, the
   2B thesis is falsified if a new higher high forms), OR a
   max_hold_days time-stop, whichever comes first.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({-1,0} position series;
        -1 = short, 0 = flat)
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


def _find_swing_highs(high: pd.Series, window: int):
    n = len(high)
    half = window // 2
    vals = high.values
    idx = []
    for i in range(half, n - half):
        window_vals = vals[i - half: i + half + 1]
        if vals[i] == window_vals.max() and (window_vals == vals[i]).sum() == 1:
            idx.append(i)
    return idx


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 9,
    max_peak_excess_pct: float = 0.05,
    trend_lookback: int = 50,
    target_pct: float = 0.10,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {-1,0} short/flat position series for 2B Top completions."""
    df = _prep(price_df)
    high, close = df["high"], df["close"]
    close_arr = close.to_numpy()
    high_arr = high.to_numpy()
    n = len(close_arr)

    sma_trend = close.rolling(trend_lookback).mean().to_numpy()
    swing_idx = _find_swing_highs(high, pivot_window)

    entries = {}  # entry_bar -> (target_price, stop_price)
    for k in range(len(swing_idx) - 1):
        b_idx, c_idx = swing_idx[k], swing_idx[k + 1]
        b_high, c_high = high_arr[b_idx], high_arr[c_idx]
        if b_high <= 0:
            continue
        excess = (c_high - b_high) / b_high
        if not (0 <= excess <= max_peak_excess_pct):
            continue  # not a "slightly above" 2B setup

        if np.isnan(sma_trend[b_idx]) or close_arr[b_idx] <= sma_trend[b_idx]:
            continue  # uptrend precondition failed

        # entry: first bar after c_idx where close falls back below b_high
        for j in range(c_idx + 1, n):
            if close_arr[j] < b_high:
                if j not in entries:
                    target_price = c_high * (1 - target_pct)
                    stop_price = c_high  # thesis falsified on a new higher high
                    entries[j] = (target_price, stop_price)
                break

    position = np.zeros(n, dtype=int)
    in_pos = False
    entry_idx = -1
    target_price = -np.inf
    stop_price = np.inf

    for t in range(n):
        if not in_pos and t in entries:
            in_pos = True
            entry_idx = t
            target_price, stop_price = entries[t]
        if in_pos:
            position[t] = -1
            held = t - entry_idx
            hit_target = close_arr[t] <= target_price
            hit_stop = close_arr[t] > stop_price
            if hit_target or hit_stop or held >= max_hold_days:
                in_pos = False

    return pd.Series(position, index=close.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs).

    Position is -1 while short; multiplying by daily returns means a
    price DROP while short (position=-1) produces a POSITIVE strategy
    return, matching a real short position's payoff.
    """
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
