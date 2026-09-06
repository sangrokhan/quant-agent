"""Strategy: Wyckoff Spring accumulation-shakeout long entry.

Hypothesis (see knowledge_base/strategies_log.jsonl):
Richard Wyckoff's "spring" pattern: within an established accumulation
range (a period of sideways consolidation), price makes a brief failed
breakdown below the range's support on relatively light volume (a shakeout
of weak-handed sellers), then reclaims support on expanding volume,
signaling that the breakdown was absorbed by "smart money" accumulation
rather than genuine distribution. Per TradingSim's explicit mechanical
rule set: "The spring entry. Setup: an accumulation zone at least two
weeks old, a break below support on light volume, then a reclaim of
support on expanding volume. Entry: the close back above support, or the
next open if it opens above support. Stop: just below the spring low.
Target: the top of the zone first, then the height of the zone projected
above it."

We operationalize this on daily bars: an "accumulation zone" is detected
as a `range_window`-day period where price stays within
`range_width_pct` of its own midpoint (a proxy for "sideways
consolidation... at least two weeks old"); "support" = the zone's rolling
low; a spring bar is one that closes/dips below support with volume BELOW
its own `vol_window`-day average (light volume), followed within
`reclaim_window` bars by a close back above support on volume ABOVE
average (expanding volume) -- the long entry trigger. Exit at the zone's
rolling high (the "top of the zone" target), on a stop breaching the spring
low, or a max_hold_days time-stop.

Source: https://www.tradingsim.com/blog/wyckoff-method-trading
("Entry and Exit Rules for Wyckoff Trades" section, read in-browser).

First Wyckoff-family strategy in this repo -- a genuinely new pattern-based
construction (volume-confirmed failed-breakdown-then-reclaim inside a
detected consolidation range) distinct from all prior breakout/mean-
reversion/divergence constructions already tested.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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
    vol_window: int = 20,
    reclaim_window: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]
    volume = df["volume"]
    n = len(close)

    range_high = close.rolling(range_window).max()
    range_low = close.rolling(range_window).min()
    range_mid = (range_high + range_low) / 2.0
    range_width = (range_high - range_low) / range_mid.replace(0, np.nan)
    in_range = range_width <= range_width_pct  # "accumulation zone" proxy

    support = range_low
    avg_vol = volume.rolling(vol_window).mean()

    below_support = (low < support) & volume.shift(0).lt(avg_vol)
    # a spring bar must occur while the PRIOR bar's rolling range still
    # qualifies as an accumulation zone (use shift(1) in_range as the
    # "established zone" context predating the shakeout)
    spring_bar = below_support & in_range.shift(1).fillna(False)

    c = close.to_numpy(dtype=float)
    spring_arr = spring_bar.to_numpy(dtype=bool)
    support_arr = support.to_numpy(dtype=float)
    range_high_arr = range_high.to_numpy(dtype=float)
    avg_vol_arr = avg_vol.to_numpy(dtype=float)
    vol_arr = volume.to_numpy(dtype=float)

    long_trigger = np.zeros(n, dtype=bool)
    spring_low_at = np.full(n, np.nan)
    target_at = np.full(n, np.nan)

    pending_spring_idx = None
    for i in range(n):
        if spring_arr[i]:
            pending_spring_idx = i
        if pending_spring_idx is not None and i > pending_spring_idx:
            if i - pending_spring_idx > reclaim_window:
                pending_spring_idx = None
                continue
            reclaimed = (
                c[i] > support_arr[pending_spring_idx]
                and vol_arr[i] > avg_vol_arr[pending_spring_idx]
            )
            if reclaimed:
                long_trigger[i] = True
                spring_low_at[i] = df["low"].iloc[pending_spring_idx]
                target_at[i] = range_high_arr[pending_spring_idx]
                pending_spring_idx = None

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_level = np.nan
    target_level = np.nan
    for i in range(n):
        if in_position:
            held = i - entry_idx
            hit_stop = c[i] < stop_level
            hit_target = c[i] >= target_level
            if hit_stop or hit_target or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if long_trigger[i]:
                in_position = True
                entry_idx = i
                stop_level = spring_low_at[i]
                target_level = target_at[i]
                position.iloc[i] = 1

    position.name = "position"
    return position


def generate_returns(
    price_df: pd.DataFrame,
    range_window: int = 15,
    range_width_pct: float = 0.08,
    vol_window: int = 20,
    reclaim_window: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        range_window=range_window,
        range_width_pct=range_width_pct,
        vol_window=vol_window,
        reclaim_window=reclaim_window,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns.name = "strategy_returns"
    return strat_returns
