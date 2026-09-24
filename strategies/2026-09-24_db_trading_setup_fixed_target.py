"""Strategy: Bulkowski's "DB Trading Setup" — double-bottom fixed-profit-target
swing trade (distinct from the breakout-continuation Double Bottom strategy
already in this repo, id 2026-09-06-180).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-137):
Per https://thepatternsite.com/DBTradingSetup.html (Thomas Bulkowski,
browser_exec), Bulkowski's disclosed mechanical rules for a double-bottom
swing-trade setup: find a confirmed swing low (5 bars before/after, an
11-bar window) at least `min_gap_days`-`max_gap_days` apart from a prior
similar-price swing low, with price having risen >= `min_rise_pct` off the
first bottom before dropping to the second. Once the second bottom's
11-day window completes, the highest high in that window becomes the
CONFIRMATION price. Buy at the next day's OPEN once close crosses above the
confirmation price. Unlike the source's own trading setup (a LIMIT order to
sell exactly at the confirmation high -- a fixed profit target rather than
riding the breakout for further gains), this repo also allows a
`max_hold_days` time-stop and a stop-loss below the second bottom's low, per
the source's own risk-management note ("place a worst case stop a penny
below the low at B").

Source's own 571-stock 2000-2010 in-sample+out-of-sample test: 70-72% win
rate, win/loss ratio 2.43-4.06, average hold 46-57 days, profitable 80% of
years over 20 years.

Distinct from 2026-09-06-180 (Double Bottom breakout-continuation, entry
= neckline breakout, exit = time-stop or pattern invalidation): this
strategy's entry trigger uses a specific 11-day-window swing-detection
methodology and its exit is a FIXED PROFIT TARGET at the confirmation
price (limit-order economics), not an open-ended trend-following exit.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series {0,1} long/flat
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _confirmed_swing_lows(low: pd.Series, window: int) -> pd.Series:
    """Boolean series: True at bar i if low[i] is the min of the
    window-bar-before/after centered window (confirmed causally: the flag
    only becomes visible `window` bars later, handled by the caller)."""
    half = window // 2
    roll_min = low.rolling(window, center=True).min()
    return low == roll_min


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 11,
    min_gap_days: int = 20,
    max_gap_days: int = 120,
    min_rise_pct: float = 0.15,
    low_similarity_pct: float = 0.05,
    profit_target_mode: bool = True,
    stop_buffer_pct: float = 0.001,
    max_hold_days: int = 90,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]
    n = len(df)
    half = swing_window // 2

    is_swing_low = _confirmed_swing_lows(low, swing_window)
    # A swing low at index i is only KNOWN as of index i+half (needs `half`
    # future bars to confirm the centered window) -- avoid lookahead.
    swing_low_known_idx = {}
    sl_vals = is_swing_low.values
    low_vals = low.values
    high_vals = high.values
    close_vals = close.values

    for i in range(n):
        if i + half < n and bool(sl_vals[i]):
            swing_low_known_idx[i] = i  # confirmed swing low at bar i

    swing_low_idxs = sorted(swing_low_known_idx.keys())

    position = pd.Series(0, index=df.index, dtype=int)

    in_position = False
    entry_idx = None
    target_price = None
    stop_price = None

    # Track the most recent "first bottom" candidate and look for a second
    # bottom forming later within [min_gap_days, max_gap_days].
    first_bottom_idx = None
    first_bottom_price = None
    seen_rise = False

    i = 0
    while i < n:
        if in_position:
            held = i - entry_idx
            hit_target = profit_target_mode and close_vals[i] >= target_price
            hit_stop = close_vals[i] <= stop_price
            hit_time = held >= max_hold_days
            position.iloc[i] = 1
            if hit_target or hit_stop or hit_time:
                in_position = False
                entry_idx = None
                target_price = None
                stop_price = None
                first_bottom_idx = None
                first_bottom_price = None
                seen_rise = False
            i += 1
            continue

        # Not in position: is bar i a newly-confirmed swing low (known as of i)?
        confirmed_here = i in swing_low_known_idx
        if confirmed_here:
            price_here = low_vals[i]
            if first_bottom_idx is None:
                first_bottom_idx = i
                first_bottom_price = price_here
                seen_rise = False
            else:
                gap = i - first_bottom_idx
                # Check for the required interim rise using max close since first bottom.
                interim_max = close_vals[first_bottom_idx:i + 1].max() if i > first_bottom_idx else price_here
                risen_enough = (interim_max / first_bottom_price - 1.0) >= min_rise_pct if first_bottom_price else False
                similar_price = (
                    first_bottom_price > 0
                    and abs(price_here - first_bottom_price) / first_bottom_price <= low_similarity_pct
                )
                if min_gap_days <= gap <= max_gap_days and risen_enough and similar_price:
                    # Second bottom confirmed at i. Confirmation window ends
                    # `half` bars later (already true since we only know this
                    # swing low as of i itself, which already required future
                    # bars up to i+half -- so the "window" is [i-half, i+half]).
                    window_end = min(i + half, n - 1)
                    conf_high = high_vals[i - half:window_end + 1].max() if i - half >= 0 else high_vals[0:window_end + 1].max()
                    conf_low = price_here
                    # Wait for close to cross above conf_high; scan forward.
                    j = window_end + 1
                    triggered = False
                    while j < n:
                        position.iloc[j - 1] = position.iloc[j - 1]  # no-op, keep flat until trigger
                        if close_vals[j] > conf_high:
                            triggered = True
                            break
                        j += 1
                        if j - i > max_gap_days:  # give up eventually
                            break
                    if triggered and j + 1 < n:
                        entry_idx = j + 1  # buy next day's open
                        target_price = conf_high
                        stop_price = conf_low * (1.0 - stop_buffer_pct)
                        in_position = True
                        i = entry_idx
                        continue
                    else:
                        # Reset search; treat this second bottom as a new first bottom.
                        first_bottom_idx = i
                        first_bottom_price = price_here
                else:
                    # Not a valid second bottom -- if it's a lower/similar
                    # low further out, restart the search from here.
                    if gap > max_gap_days or not similar_price:
                        first_bottom_idx = i
                        first_bottom_price = price_here
        i += 1

    return position.astype(float)


def generate_returns(
    price_df: pd.DataFrame,
    swing_window: int = 11,
    min_gap_days: int = 20,
    max_gap_days: int = 120,
    min_rise_pct: float = 0.15,
    low_similarity_pct: float = 0.05,
    profit_target_mode: bool = True,
    stop_buffer_pct: float = 0.001,
    max_hold_days: int = 90,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs here)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        swing_window=swing_window,
        min_gap_days=min_gap_days,
        max_gap_days=max_gap_days,
        min_rise_pct=min_rise_pct,
        low_similarity_pct=low_similarity_pct,
        profit_target_mode=profit_target_mode,
        stop_buffer_pct=stop_buffer_pct,
        max_hold_days=max_hold_days,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0.0) * daily_returns
    return strat_returns
