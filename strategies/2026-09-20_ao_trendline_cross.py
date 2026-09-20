"""Strategy: Awesome Oscillator (AO) Trendline Cross -- early momentum-fade
signal before the AO zero-line cross.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-XXX):
Per https://www.tradingsim.com/blog/awesome-oscillator ("Bonus Strategy",
explicitly described by the source as unpublished elsewhere): rather than
waiting for Bill Williams' Awesome Oscillator (AO = SMA(median_price, 5) -
SMA(median_price, 34)) to cross the zero line, draw a trendline connecting
two successive AO swing highs while AO is still ABOVE zero (a
downward-sloping trendline if the second high is lower than the first,
signalling waning bullish momentum); go short when AO's own value breaks
below that trendline -- earlier than a zero-line cross would trigger, and
per the source's own worked example, capturing more of the subsequent
decline. The bullish setup is the exact mirror: two AO swing lows below
zero, an upward-sloping trendline connecting them, go long when AO breaks
above that trendline.

Adapted to daily bars / a systematic, no-look-ahead implementation (the
source used discretionary chart-drawn trendlines on 5-minute equity
charts; we substitute a rolling swing-point detector and a linear
trendline projected forward bar-by-bar):
  1. Compute AO = SMA(median_price, ao_fast) - SMA(median_price, ao_slow)
     (5/34 per Bill Williams' original defaults).
  2. Detect local extrema of AO using a `pivot_strength`-bar fractal
     (a bar is a swing high if AO there is the max of the
     [-pivot_strength, +pivot_strength] window, confirmed pivot_strength
     bars later to avoid look-ahead).
  3. Bearish setup: the two most recent confirmed AO swing highs are both
     > 0, and the second is LOWER than the first (a declining-momentum
     signature). Project a straight line through those two points forward
     in time; go short (position=-1) the day AO's actual value closes
     below that projected line, provided AO is still > 0 at that point
     (skip the signal once AO itself has already gone negative -- that's
     just the ordinary zero-cross case, not the early-exit edge this
     strategy targets).
  4. Bullish setup is the mirror (two confirmed AO swing lows < 0, second
     HIGHER than first, go long when AO breaks above the rising
     trendline while still < 0).
  5. Exit: opposite signal, AO crossing the zero line in the trade's
     direction (the "slower" signal this strategy is designed to beat --
     once AO reaches zero the early-warning edge is spent), or a
     max_hold_days time-stop.

First "AO Trendline Cross" strategy in this repo -- distinct from the two
already-tested AO Twin Peaks variants (2026-09-04-160, 2026-09-10-094,
which are a divergence-vs-price-direction pattern using swing EXTREMA
levels directly) via instead drawing an actual trendline THROUGH the two
AO swing points and triggering on AO breaking that line, not on the AO
extrema levels themselves or a zero-cross.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({-1, 0, 1})
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    if len(df.index) > 1:
        median_gap = pd.Series(df.index).diff().median()
        if pd.notna(median_gap) and median_gap < pd.Timedelta(hours=20):
            df = df.resample("1D").agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                }
            ).dropna()
    return df


def _awesome_oscillator(df: pd.DataFrame, ao_fast: int, ao_slow: int) -> pd.Series:
    median_price = (df["high"] + df["low"]) / 2.0
    return median_price.rolling(ao_fast).mean() - median_price.rolling(ao_slow).mean()


def _find_confirmed_pivots(values: np.ndarray, pivot_strength: int, kind: str) -> np.ndarray:
    """Return a boolean array marking bars that are confirmed local
    extrema (high or low) `pivot_strength` bars ago (confirmation lag
    avoids look-ahead: we only know bar t was a pivot once we've seen
    t+pivot_strength)."""
    n = len(values)
    is_pivot = np.zeros(n, dtype=bool)
    for i in range(pivot_strength, n - pivot_strength):
        window = values[i - pivot_strength : i + pivot_strength + 1]
        center = values[i]
        if np.isnan(center) or np.isnan(window).any():
            continue
        if kind == "high" and center == window.max() and np.sum(window == center) == 1:
            is_pivot[i] = True
        elif kind == "low" and center == window.min() and np.sum(window == center) == 1:
            is_pivot[i] = True
    return is_pivot


def generate_signals(
    price_df: pd.DataFrame,
    ao_fast: int = 5,
    ao_slow: int = 34,
    pivot_strength: int = 3,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {-1, 0, 1} position series."""
    df = _prep(price_df)
    n = len(df)
    ao = _awesome_oscillator(df, ao_fast, ao_slow)
    ao_v = ao.values

    is_high = _find_confirmed_pivots(ao_v, pivot_strength, "high")
    is_low = _find_confirmed_pivots(ao_v, pivot_strength, "low")

    position = np.zeros(n, dtype=int)
    current_pos = 0
    entry_idx = -1

    # Track last two confirmed swing highs / lows (index, value) available
    # as of each bar (respecting the confirmation lag).
    last_two_highs: list[tuple[int, float]] = []
    last_two_lows: list[tuple[int, float]] = []

    for i in range(n):
        # A pivot at position (i - pivot_strength) becomes confirmed/known at bar i.
        confirm_idx = i - pivot_strength
        if confirm_idx >= 0:
            if is_high[confirm_idx]:
                last_two_highs.append((confirm_idx, ao_v[confirm_idx]))
                if len(last_two_highs) > 2:
                    last_two_highs.pop(0)
            if is_low[confirm_idx]:
                last_two_lows.append((confirm_idx, ao_v[confirm_idx]))
                if len(last_two_lows) > 2:
                    last_two_lows.pop(0)

        if np.isnan(ao_v[i]):
            position[i] = current_pos
            continue

        if current_pos != 0:
            held = i - entry_idx
            exit_now = held >= max_hold_days
            if current_pos == 1 and ao_v[i] <= 0:
                exit_now = True
            if current_pos == -1 and ao_v[i] >= 0:
                exit_now = True
            if exit_now:
                current_pos = 0
            position[i] = current_pos
            if current_pos != 0:
                continue

        # Only look for new entries when flat.
        if current_pos == 0:
            # Bearish trendline-break setup.
            if len(last_two_highs) == 2:
                (i1, v1), (i2, v2) = last_two_highs
                if i2 > i1 and v1 > 0 and v2 > 0 and v2 < v1:
                    slope = (v2 - v1) / (i2 - i1)
                    projected = v1 + slope * (i - i1)
                    if ao_v[i] < projected and ao_v[i] > 0:
                        current_pos = -1
                        entry_idx = i

            # Bullish trendline-break setup (only if not already entered short).
            if current_pos == 0 and len(last_two_lows) == 2:
                (i1, v1), (i2, v2) = last_two_lows
                if i2 > i1 and v1 < 0 and v2 < 0 and v2 > v1:
                    slope = (v2 - v1) / (i2 - i1)
                    projected = v1 + slope * (i - i1)
                    if ao_v[i] > projected and ao_v[i] < 0:
                        current_pos = 1
                        entry_idx = i

        position[i] = current_pos

    return pd.Series(position, index=df.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strategy_ret
