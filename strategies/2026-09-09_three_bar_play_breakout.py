"""Strategy: 3 Bar Play momentum continuation, adapted to daily bars.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-006):
Per TradingSim's "The 3 Bar Play Pattern: Entry, Stop & Target Rules"
(https://www.tradingsim.com/blog/3-bar-play, fully disclosed): a wide-range
"igniting" bar (strong directional move, ideally on high volume) followed
by a tight pullback bar (or two) that does NOT retrace more than 50% of
the igniting bar's range signals a low-risk continuation setup; entry is a
breakout above the pullback bar's high, stop below the pullback bar's low.
Designed originally for intraday (1-2 minute) charts around the market
open, but the mechanical logic (strong impulse -> tight consolidation ->
breakout continuation) generalizes to daily bars as a trend-day + 1-day
pullback + breakout pattern. First "wide-range-bar + tight-pullback +
breakout" pattern strategy in this repo -- distinct from NR7/NR4
(narrowest-of-N-bars contraction, no requirement for a preceding wide
igniting bar) and from Bullish Kicker/Gap-and-Go (gap-based triggers, not
an intrabar range-expansion trigger).

Signal logic
------------
- Igniting bar: true range (high-low) on day t-1 is >= ignite_range_ratio
  times the trailing avg_window-day average true range, AND day t-1 closed
  green (close > open) -- a strong bullish impulse day.
- Pullback bar: day t's range is <= pullback_max_pct of the igniting bar's
  range, AND day t's low stays above 50% retracement of the igniting bar's
  range (source's own "must not exceed 50% retracement" rule).
- Entry (long): day t+1 (or later, within a short window) breaks above the
  pullback bar's high -> enter at that day's close.
- Stop-loss: below the pullback bar's low (source's own stop rule).
- Exit: stop hit, OR a max_hold_days safety time-stop (source doesn't
  specify a target here; using a time-stop backstop, consistent with this
  repo's convention).
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
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
    avg_window: int = 20,
    ignite_range_ratio: float = 1.5,
    pullback_max_pct: float = 0.5,
    breakout_window: int = 3,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, high, low, open_ = df["close"], df["high"], df["low"], df["open"]
    n = len(close)

    true_range = (high - low).abs()
    avg_range = true_range.rolling(avg_window).mean()

    is_igniting = (true_range >= ignite_range_ratio * avg_range) & (close > open_)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_count = 0
    stop_price = None

    pending_pullback_high = None
    pending_pullback_low = None
    pending_ignite_idx = None
    pending_bars_waited = 0

    for i in range(1, n):
        if in_position:
            hold_count += 1
            if (stop_price is not None and close.iloc[i] < stop_price) or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                stop_price = None
            else:
                position.iloc[i] = 1
            continue

        # Check for an active pullback bar waiting for breakout
        if pending_pullback_high is not None:
            pending_bars_waited += 1
            if close.iloc[i] > pending_pullback_high:
                in_position = True
                hold_count = 0
                stop_price = pending_pullback_low
                position.iloc[i] = 1
                pending_pullback_high = None
                pending_pullback_low = None
                pending_ignite_idx = None
                pending_bars_waited = 0
                continue
            elif pending_bars_waited >= breakout_window:
                # give up waiting
                pending_pullback_high = None
                pending_pullback_low = None
                pending_ignite_idx = None
                pending_bars_waited = 0

        # Check if yesterday was an igniting bar and today is a valid tight pullback
        if pending_pullback_high is None and is_igniting.iloc[i - 1]:
            ignite_range = (high.iloc[i - 1] - low.iloc[i - 1])
            if ignite_range > 0:
                today_range = high.iloc[i] - low.iloc[i]
                retrace_50pct_level = high.iloc[i - 1] - 0.5 * ignite_range
                is_tight_pullback = (
                    today_range <= pullback_max_pct * ignite_range
                    and low.iloc[i] >= retrace_50pct_level
                )
                if is_tight_pullback:
                    pending_pullback_high = high.iloc[i]
                    pending_pullback_low = low.iloc[i]
                    pending_ignite_idx = i - 1
                    pending_bars_waited = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    avg_window: int = 20,
    ignite_range_ratio: float = 1.5,
    pullback_max_pct: float = 0.5,
    breakout_window: int = 3,
    max_hold_days: int = 10,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        avg_window=avg_window,
        ignite_range_ratio=ignite_range_ratio,
        pullback_max_pct=pullback_max_pct,
        breakout_window=breakout_window,
        max_hold_days=max_hold_days,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(float) * daily_returns
    return strat_returns
