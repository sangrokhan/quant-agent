"""Strategy: Bulkowski Pothole Pattern (bullish continuation, long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/Pothole.html (Thomas Bulkowski,
browser_exec fallback -- web_search's DDGS backend cannot extract this
domain). Source's own disclosed identification rules and statistics:

    "In an uptrend, traders see the stock moving sideways (forming the
    'road'), and then dropping into a pothole. The move looks like a
    downward breakout, and it is, but the stock soon recovers. In fact,
    price continues higher, shooting out the top of the pattern and
    soaring... Overall performance rank... 4 out of 40. Break even
    failure rate: 9%. Average rise: 51%. Percentage meeting price target:
    86%... Price trend: Upward leading to the start of the chart pattern.
    Shape: A flat road (horizontal movement) followed by a dip (the
    pothole). After the pothole, price rises and shoots out the top of
    the pattern. Flat base: Prices along the bottom of the pothole
    pattern should be horizontal, or nearly so... Pothole: After the flat
    base, a pothole appears. This can be a quick one-day plunge which
    sees price drop below the flat base, or it can last for a few
    weeks... Breakout, confirmation: The breakout occurs when price
    closes above the top of the pothole pattern."

Rank 4/40 and a 9% break-even failure rate are among the strongest
disclosed statistics of any Bulkowski pattern sourced in this repo.
Critically, unlike several recently-tested Bulkowski patterns (Pipe
Bottom, Horn Bottom), the source explicitly says this pattern is designed
for the DAILY scale ("Look for potholes on the daily charts or on shorter
time frames. For weekly or monthly scale, consider the diving board.") --
no scale-mismatch caveat applies here, making it a cleaner test of this
repo's existing daily-bar-only pipeline.

First "Pothole" strategy in this repo (0 prior index hits) -- distinct
from every other pattern tested: it requires a flat/horizontal
consolidation BASE first, then a sharp single/few-bar PLUNGE below that
base, then a V-shaped recovery breaking back above the base's top -- not a
gradual bowl (Rounding Bottom), not parallel/converging trendlines
(Rectangle/Triangle), not two similar-depth spikes (Horn/Pipe Bottom).

Signal logic (numeric proxy for the source's qualitative flat-road +
plunge + recovery shape)
------------------------------------------------------------------------
1. Flat base detection: over a rolling `base_window`-bar lookback ending
   at bar i, the base is "flat" if the coefficient of variation of closes
   in that window is below `base_flatness_pct` (numeric proxy for "prices
   along the bottom... should be horizontal, or nearly so").
2. Uptrend precondition (source: "Price trend: Upward leading to the
   start of the chart pattern"): close at the start of the base window is
   above its own SMA(trend_lookback).
3. Pothole plunge: within `plunge_window` bars immediately after the flat
   base, price must drop at least `plunge_depth_pct` below the base's own
   minimum close (source: "a quick one-day plunge which sees price drop
   below the flat base, or it can last for a few weeks").
4. Confirmation/entry: the first bar after the plunge's own local minimum
   where close closes above the base's own MAXIMUM close (the "top of the
   pothole pattern," source's own confirmation rule) -- long entry on that
   bar.
5. Exit: source's own Measure Rule (height = base top - plunge low, target
   = base top + height * target_pct, source's own disclosed 86%
   "percentage meeting price target"), OR close falls back below the
   base's own bottom (source's own stop-loss location: "The bottom of the
   flat base... serves as a good stop location"), OR a max_hold_days
   time-stop, whichever comes first.

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
    base_window: int = 15,
    base_flatness_pct: float = 0.03,
    trend_lookback: int = 50,
    plunge_window: int = 10,
    plunge_depth_pct: float = 0.03,
    target_pct: float = 0.86,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series for Pothole completions."""
    df = _prep(price_df)
    close = df["close"]
    close_arr = close.to_numpy()
    n = len(close_arr)

    sma_trend = close.rolling(trend_lookback).mean().to_numpy()

    # Rolling stats over the trailing base_window ending at each bar.
    roll = close.rolling(base_window)
    roll_mean = roll.mean().to_numpy()
    roll_std = roll.std().to_numpy()
    roll_max = roll.max().to_numpy()
    roll_min = roll.min().to_numpy()

    patterns = []  # (base_end_idx, base_top, base_bottom)
    for base_end in range(base_window, n - 1):
        base_start = base_end - base_window
        mean_c = roll_mean[base_end]
        std_c = roll_std[base_end]
        if np.isnan(mean_c) or mean_c <= 0 or np.isnan(std_c):
            continue
        cv = std_c / mean_c
        if cv > base_flatness_pct:
            continue  # not flat enough
        if np.isnan(sma_trend[base_start]) or close_arr[base_start] <= sma_trend[base_start]:
            continue  # uptrend precondition failed

        base_top = roll_max[base_end]
        base_bottom = roll_min[base_end]

        # Pothole plunge search within plunge_window bars after base_end.
        plunge_end = min(n, base_end + 1 + plunge_window)
        if plunge_end <= base_end + 1:
            continue
        window_lows = close_arr[base_end + 1: plunge_end]
        if len(window_lows) == 0:
            continue
        plunge_min = window_lows.min()
        plunge_min_offset = int(np.argmin(window_lows))
        plunge_idx = base_end + 1 + plunge_min_offset

        if base_bottom <= 0:
            continue
        depth = (base_bottom - plunge_min) / base_bottom
        if depth < plunge_depth_pct:
            continue  # not a deep enough plunge

        patterns.append((plunge_idx, base_top, base_bottom))

    # Confirmation entries: first bar after plunge_idx where close > base_top.
    entries = {}
    for plunge_idx, base_top, base_bottom in patterns:
        for j in range(plunge_idx + 1, n):
            if close_arr[j] > base_top:
                if j not in entries:
                    height = base_top - min(close_arr[plunge_idx], base_bottom)
                    if height <= 0:
                        break
                    target_price = base_top + height * target_pct
                    entries[j] = (target_price, base_bottom)
                break

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
            hit_target = close_arr[t] >= target_price
            hit_stop = close_arr[t] < stop_price
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
