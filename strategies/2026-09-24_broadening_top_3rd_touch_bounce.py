"""Strategy: Bulkowski Broadening Top -- "Buy at 3rd Touch" of the lower
(descending) trendline (long-only bounce trade).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/bt.html (Thomas Bulkowski,
browser_exec fallback -- web_search's DDGS backend cannot `extract` this
domain's page content). Source's own disclosed identification rules and
trading tactic:

    "Shape: Higher peaks and lower valleys -- a megaphone shape.
    Trendlines: The top trendline slopes upward, the bottom one slopes
    downward to highlight a broadening pattern. Touches: At least five
    touches total, three peaks or three valleys should touch the
    associated trend line with two or more touches of the other
    trendline... Buy at 3rd touch: When price touches the bottom
    trendline for the third time (C) and begins rising, buy. Warning:
    This is a high risk entry."

The source's own stats for this pattern are mediocre (upward-breakout
overall rank 22/39, break-even failure rate 18%, average rise 42%) -- a
materially weaker prior than most Bulkowski patterns already accepted in
this repo, but the source explicitly discloses a precise, numerically
testable entry rule ("3rd touch of the lower trendline") distinct from
every other chart-pattern strategy in this repo, which is what makes it
worth testing on its own (rather than the more commonly-tested single
breakout-confirmation entry).

First "Broadening Top"/"megaphone" pattern strategy in this repo (0 prior
index hits for "broadening top"; the companion "broadening bottom" pattern
was already visited/tested this cron trigger's history at
thepatternsite.com/broadb.html but is a mirror-image DOWNTREND-into pattern,
distinct from this UPTREND-into Broadening Top).

Signal logic (numeric proxy for the source's qualitative megaphone shape
and "3rd touch" trading tactic)
------------------------------------------------------------------------
1. Swing pivot detection: same rolling-window fractal test used elsewhere
   in this repo (e.g. inverse Head & Shoulders) to find alternating swing
   highs/lows over `pivot_window`.
2. For each new swing LOW (a candidate "touch" of the lower/descending
   trendline), look back over the trailing `pattern_lookback` bars and
   collect all swing highs and swing lows in that window.
3. Megaphone validity: require >= `min_lows` swing lows (this one being
   the count-th touch) AND >= `min_highs` swing highs within the window.
   Fit a linear regression (np.polyfit) through the swing highs (must have
   POSITIVE slope, "top trendline slopes upward") and through the swing
   lows (must have NEGATIVE slope, "bottom trendline slopes downward") --
   this is the numeric proxy for the source's megaphone shape requirement.
4. "3rd touch" trigger: when the count of swing lows within the window
   reaches exactly `touch_count` (source's own tactic: "when price touches
   the bottom trendline for the THIRD time"), and the immediately
   following bar's close is higher than this swing low's close (source's
   own "and begins rising" confirmation), enter LONG on that next bar.
5. Exit: source's own Measure Rule (height = highest swing high - lowest
   swing low in the pattern window; target = pattern's top swing high +
   height * target_pct, source's own disclosed 66% "percentage meeting
   price target" for upward breakouts), OR close falls back below the
   lowest swing low in the window (failed bounce / trendline breakdown),
   OR a max_hold_days time-stop, whichever comes first.

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


def _find_pivots(series: pd.Series, window: int) -> pd.Series:
    n = len(series)
    pivots = pd.Series(0, index=series.index, dtype=int)
    half = window // 2
    vals = series.values
    for i in range(half, n - half):
        window_vals = vals[i - half : i + half + 1]
        if vals[i] == window_vals.max() and (window_vals == vals[i]).sum() == 1:
            pivots.iloc[i] = 1
        elif vals[i] == window_vals.min() and (window_vals == vals[i]).sum() == 1:
            pivots.iloc[i] = -1
    return pivots


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 9,
    pattern_lookback: int = 90,
    touch_count: int = 3,
    min_highs: int = 2,
    target_pct: float = 0.66,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series for the 'buy at 3rd touch'
    Broadening Top bounce tactic."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]
    c_arr = close.values
    n = len(c_arr)

    high_pivots = _find_pivots(high, pivot_window)
    low_pivots = _find_pivots(low, pivot_window)

    swing_highs = [(i, float(high.iloc[i])) for i in range(n) if high_pivots.iloc[i] == 1]
    swing_lows = [(i, float(low.iloc[i])) for i in range(n) if low_pivots.iloc[i] == -1]

    def highs_in_window(start_idx, end_idx):
        return [(i, p) for i, p in swing_highs if start_idx <= i <= end_idx]

    def lows_in_window(start_idx, end_idx):
        return [(i, p) for i, p in swing_lows if start_idx <= i <= end_idx]

    # For each swing low (candidate "touch"), check if it's the touch_count-th
    # touch within its own trailing pattern_lookback window, and if the
    # megaphone-shape validity conditions hold.
    entries = {}  # entry_bar -> (target_price, stop_price)
    for k, (low_idx, low_price) in enumerate(swing_lows):
        window_start = max(0, low_idx - pattern_lookback)
        lows_w = lows_in_window(window_start, low_idx)
        if len(lows_w) != touch_count:
            continue  # only trigger exactly at the touch_count-th touch
        highs_w = highs_in_window(window_start, low_idx)
        if len(highs_w) < min_highs:
            continue

        low_x = np.array([i for i, _ in lows_w], dtype=float)
        low_y = np.array([p for _, p in lows_w], dtype=float)
        high_x = np.array([i for i, _ in highs_w], dtype=float)
        high_y = np.array([p for _, p in highs_w], dtype=float)

        if len(set(low_x)) < 2 or len(set(high_x)) < 2:
            continue
        low_slope = np.polyfit(low_x, low_y, 1)[0]
        high_slope = np.polyfit(high_x, high_y, 1)[0]

        if not (low_slope < 0 and high_slope > 0):
            continue  # not a valid megaphone (bottom must descend, top must ascend)

        # entry: the bar right after this swing low, if close rises
        entry_bar = low_idx + 1
        if entry_bar >= n:
            continue
        if c_arr[entry_bar] <= c_arr[low_idx]:
            continue  # source's own "and begins rising" confirmation failed

        pattern_top = max(p for _, p in highs_w)
        pattern_bottom = min(p for _, p in lows_w)
        height = pattern_top - pattern_bottom
        if height <= 0:
            continue
        target_price = pattern_top + height * target_pct
        stop_price = pattern_bottom

        if entry_bar not in entries:  # first qualifying pattern wins the bar
            entries[entry_bar] = (target_price, stop_price)

    position = np.zeros(n, dtype=int)
    in_pos = False
    entry_idx = -1
    target_price = np.inf
    stop_price = -np.inf

    for t in range(n):
        if not in_pos and t in entries:
            in_pos = True
            entry_idx = t
            target_price, stop_price = entries[t]
        if in_pos:
            position[t] = 1
            held = t - entry_idx
            hit_target = c_arr[t] >= target_price
            hit_stop = c_arr[t] < stop_price
            if hit_target or hit_stop or held >= max_hold_days:
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
