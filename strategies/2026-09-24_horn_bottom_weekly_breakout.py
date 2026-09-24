"""Strategy: Bulkowski Horn Bottom chart pattern (weekly-scale, long-only),
resampled from this repo's daily OHLCV loaders per the source's own
explicit requirement that the pattern be identified on the WEEKLY chart.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/hornb.html (Thomas Bulkowski,
browser_exec fallback -- web_search's DDGS backend cannot usefully extract
this domain, as with every prior thepatternsite.com entry this cron
trigger).

Source's own disclosed identification rules and statistics (one of the
strongest-performing patterns encountered on thepatternsite.com this cron
trigger):
    "Horn bottoms are H-shaped chart patterns... Discovered by Thomas
    Bulkowski in 1998. Weekly chart: use the weekly chart to locate
    horns. Price trend: downward leading to the pattern. Shape: Looks
    like an inverted steer's horn, two parallel price spikes separated
    by a week [i.e. two weekly lows one week apart, with a middle week
    between them]. Spikes: should plummet below the surrounding price
    landscape, including the middle week. Confirmation: valid when price
    closes above the highest price in the 3-week pattern."
    Overall performance rank: 2/3 (weekly scale) -- among the best
    patterns disclosed on this site. Break-even failure rate: 6% (very
    low). Average rise: 59%. Percentage meeting price target: 74%.
    Source's own disclosed Measure Rule: "Compute the height from the
    highest price (A) to lowest price (B) in the 3-week pattern, multiply
    by the 74% target-meeting rate, add to the highest high (A) to get
    the target (C)."

This is a WEEKLY-scale pattern -- this repo's data loaders provide daily
OHLCV only, so this strategy resamples the daily bars to weekly bars
in-process (standard W-FRI resampling: weekly open/high/low/close/volume)
before detecting the pattern, then maps the weekly confirmation signal
back onto the underlying daily index (position held from the daily bar
following weekly confirmation through the weekly-bar-equivalent exit),
consistent Rather than reimplementing OHLCV fetch logic per RESEARCH_LOOP.md
Step 5's constraint of only using data/loaders.py for the raw fetch.

First "Horn Bottom" strategy in this repo (0 prior index hits) -- distinct
from every other pattern already tested (this is the first genuinely
weekly-timeframe pattern tested this cron trigger; all prior candlestick
patterns this trigger used daily bars).

Signal logic (numeric proxy for the source's disclosed identification
guidelines + Trading Tips)
------------------------------------------------------------------------
1. Resample daily OHLCV to weekly bars (W-FRI).
2. Downtrend context (source's own required setup): weekly close[w-2]
   below SMA(trend_window) evaluated in weekly bars.
3. Two-spike shape: weekly low[w-2] and weekly low[w] both plummet below
   the surrounding landscape -- proxied as both being local minima
   relative to their own `spike_lookback`-week trailing window, and each
   at least `spike_min_pct` below the middle week's low (weekly low[w-1]).
4. Confirmation: weekly close exceeds the highest weekly high across the
   3-week pattern (w-2, w-1, w) -- long entry the first subsequent WEEK
   whose close exceeds that level, mapped to the daily bar at that week's
   close.
5. Exit: source's own Measure Rule (height = pattern_high - pattern_low,
   target = breakout_price + height * target_pct) OR weekly close falls
   back below the pattern low (failed breakout stop) OR a
   max_hold_weeks time-stop, whichever comes first -- evaluated on
   weekly bars and mapped back to daily position.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series, daily index)
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


def _resample_weekly(df: pd.DataFrame) -> pd.DataFrame:
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if "volume" in df.columns:
        agg["volume"] = "sum"
    weekly = df.resample("W-FRI").agg(agg).dropna(subset=["close"])
    return weekly


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 10,
    spike_lookback: int = 8,
    spike_min_pct: float = 0.005,
    target_pct: float = 0.74,
    max_hold_weeks: int = 12,
) -> pd.Series:
    """Return a {0,1} daily long/flat position series for Horn Bottom
    completions identified on a weekly resample of the daily OHLCV."""
    df = _prep(price_df)
    weekly = _resample_weekly(df)
    wh, wl, wc = weekly["high"], weekly["low"], weekly["close"]
    nw = len(wc)

    sma = wc.rolling(trend_window).mean()

    wh_a = wh.to_numpy()
    wl_a = wl.to_numpy()
    wc_a = wc.to_numpy()
    sma_a = sma.to_numpy()

    roll_low = wl.rolling(spike_lookback).min()
    roll_low_a = roll_low.to_numpy()

    weekly_entries: dict[int, tuple[float, float]] = {}

    for w in range(2, nw):
        a, mid, b = w - 2, w - 1, w
        if np.isnan(sma_a[a]) or wc_a[a] >= sma_a[a]:
            continue
        if np.isnan(roll_low_a[a]) or np.isnan(roll_low_a[b]):
            continue
        # both spikes should plummet notably below the surrounding
        # landscape (proxied by their own trailing rolling low, within a
        # small tolerance rather than requiring an exact tie for the
        # minimum) and below the middle week's low
        spike_a_is_low = wl_a[a] <= roll_low_a[a] * 1.01
        spike_b_is_low = wl_a[b] <= roll_low_a[b] * 1.01
        if not (spike_a_is_low and spike_b_is_low):
            continue
        mid_low = wl_a[mid]
        if mid_low <= 0:
            continue
        below_mid_a = (mid_low - wl_a[a]) / mid_low >= spike_min_pct
        below_mid_b = (mid_low - wl_a[b]) / mid_low >= spike_min_pct
        if not (below_mid_a and below_mid_b):
            continue

        pattern_high = max(wh_a[a], wh_a[mid], wh_a[b])
        pattern_low = min(wl_a[a], wl_a[b])
        height = pattern_high - pattern_low
        if height <= 0:
            continue
        target_price = pattern_high + height * target_pct
        stop_price = pattern_low

        for j in range(b + 1, nw):
            if wc_a[j] > pattern_high:
                if j not in weekly_entries:
                    weekly_entries[j] = (target_price, stop_price)
                break

    weekly_position = np.zeros(nw, dtype=int)
    in_pos = False
    entry_idx = -1
    target_price = np.inf
    stop_price = -np.inf

    for w in range(nw):
        if not in_pos and w in weekly_entries:
            in_pos = True
            entry_idx = w
            target_price, stop_price = weekly_entries[w]
        if in_pos:
            weekly_position[w] = 1
            held = w - entry_idx
            hit_target = wc_a[w] >= target_price
            hit_stop = wc_a[w] < stop_price
            if hit_target or hit_stop or held >= max_hold_weeks:
                in_pos = False

    weekly_pos_series = pd.Series(weekly_position, index=weekly.index)

    # Map weekly position back onto the daily index: a position held for
    # week w applies to all daily bars strictly after that week's Friday
    # close through the end of the position (reindex forward-fill on the
    # weekly Friday timestamps, then align to daily index).
    daily_position = weekly_pos_series.reindex(df.index, method="ffill").fillna(0).astype(int)
    return daily_position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
