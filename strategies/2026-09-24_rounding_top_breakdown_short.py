"""Strategy: Bulkowski Rounding Top breakout (bearish reversal SHORT).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/roundingtop.html (Thomas
Bulkowski, browser_exec fallback -- web_search's DDGS backend cannot
extract this domain). Source's own disclosed identification rules and
statistics:

    "Rounded turn: Prices form a gentle curve, a half moon shape...
    Breakout: A close above the highest high signals an upward breakout.
    Downward breakouts are a close below the lower of the two rims (the
    lowest low in the pattern)... Overall performance rank for up/down
    breakouts (1 is best): 2 out of 39 / 3 out of 36. Break even failure
    rate for up/down breakouts: 9%/20%. Average rise/decline: 55%/17%."

This is the mirror-image top-formation counterpart of this cron trigger's
already-accepted Rounding Bottom (2026-09-24-101/102, a smooth U-shaped
bowl decline-then-recovery). Rounding Top is a smooth inverted-U/half-moon
rise-then-decline, and this strategy trades its DOWNWARD breakout
(source's own disclosed rank 3/36 for down breakouts -- still a strong,
if slightly weaker than upward, prior) as a SHORT position (simulated
only, position=-1, per SAFETY.md's simulation-only scope, consistent with
this cron trigger's earlier 2B Top and Busted H&S Bottom short
strategies).

First "Rounding Top" strategy in this repo (0 prior index hits) --
distinct from Rounding Bottom via trading the opposite curve direction and
the opposite (downward) breakout confirmation.

Signal logic (numeric proxy for the source's qualitative half-moon shape
and downward-breakout confirmation rule, mirroring
2026-09-24_rounding_bottom_breakout.py's already-validated approach)
------------------------------------------------------------------------
1. Peak detection: over a rolling `bowl_window`-bar lookback, find the
   bar-index of the MAXIMUM close (the "highest peak," per source). A
   valid rounding-top candidate requires that maximum to fall roughly in
   the MIDDLE of the window (within `center_tolerance` of the window's
   midpoint, a numeric proxy for "gentle turn" symmetry) -- this
   discourages simple sharp spike-tops from qualifying.
2. Left rim: the close at the start of the bowl window (`left_rim`).
3. Prior uptrend filter: close at the start of the bowl window is above
   its own SMA(trend_lookback) (source: "Price trend: Upward leading to
   the chart pattern").
4. Entry (SHORT): the first bar after the peak where close closes below
   `left_rim` (source's own downward-breakout confirmation rule uses the
   lower of the two rims -- here approximated by the left rim as the
   confirmation trigger, mirroring the Rounding Bottom file's own
   left-lip-confirmation convention).
5. Exit: source's own Measure Rule (height = peak_price - left_rim,
   target = left_rim - height * target_pct, source's own disclosed 14%
   "percentage meeting price target" for downward breakouts), OR close
   rises back above the peak price (failed breakdown, stop-loss), OR a
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


def generate_signals(
    price_df: pd.DataFrame,
    bowl_window: int = 60,
    center_tolerance: float = 0.30,
    trend_lookback: int = 50,
    target_pct: float = 0.14,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {-1,0} short/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    close_arr = close.to_numpy()
    n = len(close_arr)

    sma_trend = close.rolling(trend_lookback).mean()
    sma_arr = sma_trend.to_numpy()

    entries_trigger = np.zeros(n, dtype=bool)
    left_rims = np.full(n, np.nan)
    peak_prices = np.full(n, np.nan)

    mid_tol = center_tolerance * bowl_window

    for i in range(bowl_window, n):
        window = close_arr[i - bowl_window: i]
        peak_offset = int(np.argmax(window))
        peak_price = window[peak_offset]
        mid = bowl_window / 2.0
        if abs(peak_offset - mid) > mid_tol:
            continue
        left_rim = window[0]
        left_rim_bar = i - bowl_window
        if np.isnan(sma_arr[left_rim_bar]) or close_arr[left_rim_bar] <= sma_arr[left_rim_bar]:
            continue  # prior uptrend filter failed
        if peak_offset < bowl_window - 1 and close_arr[i] < left_rim:
            entries_trigger[i] = True
            left_rims[i] = left_rim
            peak_prices[i] = peak_price

    position = np.zeros(n, dtype=int)
    in_pos = False
    entry_bar = -1
    entry_rim = np.nan
    entry_peak = np.nan
    target_price = np.nan

    for t in range(n):
        if entries_trigger[t] and not in_pos:
            in_pos = True
            entry_bar = t
            entry_rim = left_rims[t]
            entry_peak = peak_prices[t]
            height = entry_peak - entry_rim
            target_price = entry_rim - height * target_pct if height > 0 else -np.inf
        if in_pos:
            position[t] = -1
            held = t - entry_bar
            failed = close_arr[t] > entry_peak
            hit_target = close_arr[t] <= target_price
            if failed or hit_target or held >= max_hold_days:
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
