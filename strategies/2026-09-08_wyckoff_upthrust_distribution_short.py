"""Strategy: Wyckoff Upthrust distribution-shakeout short entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-039):
Richard Wyckoff's "upthrust" pattern is the distribution-phase mirror
image of the already-tested "spring" accumulation pattern (rejected,
id=2026-09-06-123): within an established distribution range (period of
sideways consolidation after an advance), price makes a brief false
breakout ABOVE the range's resistance -- trapping late buyers -- then
reverses sharply back inside the range as "smart money" distributes
(sells) into the trapped demand.

Per https://algobars.com/strategy-templates/wyckoff-complete/wyckoff-upthrust/
("The Upthrust is the distribution equivalent of the Spring. Price spikes
above resistance to trap buyers, then reverses sharply as smart money
distributes." Rules: "Identify distribution range (Phase A-C); Price
breaks above range resistance (Upthrust); Volume may be high but no
follow-through; Price falls back into range quickly; Enter short on
failure candle; Target: Bottom of range, then markdown."), corroborated
by the general Wyckoff literature's upthrust definition (spike above
resistance on volume, with NO follow-through/sustained new-high
persistence, followed by a fast reversal back inside the range).

Operationalized on daily bars: a "distribution range" is detected as a
`range_window`-day period where price stays within `range_width_pct` of
its own midpoint (same consolidation-detection proxy as the Spring
strategy, for direct comparability); "resistance" = the zone's rolling
high; an upthrust bar is one whose high spikes above resistance but
closes back INSIDE the range that same bar or within `reclaim_window`
bars (the "no follow-through, falls back in quickly" failure signature)
-- the short entry trigger, on the failure-confirmation close. Exit at
the zone's rolling low (the "bottom of range" target), a stop above the
upthrust high, or a max_hold_days time-stop.

Distinct from the rejected Wyckoff Spring (2026-09-06-123, long-only
accumulation mirror) by being the short-side distribution mirror -- same
range-detection mechanism, opposite direction and breakout-failure
condition (false breakOUT above resistance vs false breakDOWN below
support).

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py).
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
    range_window: int = 15,
    range_width_pct: float = 0.08,
    reclaim_window: int = 3,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {-1,0} short/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    n = len(close)

    range_high = close.rolling(range_window).max()
    range_low = close.rolling(range_window).min()
    range_mid = (range_high + range_low) / 2.0
    range_width = (range_high - range_low) / range_mid.replace(0, np.nan)
    in_range = range_width <= range_width_pct  # "distribution zone" proxy

    resistance = range_high
    above_resistance = high > resistance
    # upthrust bar: spikes above resistance while the PRIOR bar's rolling
    # range still qualifies as a distribution zone (established range)
    upthrust_bar = above_resistance & in_range.shift(1).fillna(False)

    c = close.to_numpy(dtype=float)
    h = high.to_numpy(dtype=float)
    upthrust_arr = upthrust_bar.to_numpy(dtype=bool)
    resistance_arr = resistance.to_numpy(dtype=float)
    range_low_arr = range_low.to_numpy(dtype=float)

    short_trigger = np.zeros(n, dtype=bool)
    upthrust_high_at = np.full(n, np.nan)
    target_at = np.full(n, np.nan)

    pending_upthrust_idx = None
    for i in range(n):
        if upthrust_arr[i]:
            pending_upthrust_idx = i
        if pending_upthrust_idx is not None and i >= pending_upthrust_idx:
            if i - pending_upthrust_idx > reclaim_window:
                pending_upthrust_idx = None
                continue
            # failure confirmation: close falls back below resistance
            # (the false-breakout is rejected, no follow-through)
            failed = c[i] < resistance_arr[pending_upthrust_idx]
            if failed and i > pending_upthrust_idx:
                short_trigger[i] = True
                upthrust_high_at[i] = h[pending_upthrust_idx]
                target_at[i] = range_low_arr[pending_upthrust_idx]
                pending_upthrust_idx = None

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_level = np.nan
    target_level = np.nan
    for i in range(n):
        if in_position:
            held = i - entry_idx
            hit_stop = c[i] > stop_level
            hit_target = c[i] <= target_level
            if hit_stop or hit_target or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = -1
        else:
            if short_trigger[i]:
                in_position = True
                entry_idx = i
                stop_level = upthrust_high_at[i]
                target_level = target_at[i]
                position.iloc[i] = -1

    position.name = "position"
    return position


def generate_returns(
    price_df: pd.DataFrame,
    range_window: int = 15,
    range_width_pct: float = 0.08,
    reclaim_window: int = 3,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        range_window=range_window,
        range_width_pct=range_width_pct,
        reclaim_window=reclaim_window,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns.name = "strategy_returns"
    return strat_returns
