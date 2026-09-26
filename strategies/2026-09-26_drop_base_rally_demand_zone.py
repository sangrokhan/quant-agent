"""Strategy: Drop-Base-Rally (DBR) Demand Zone retest, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from AlgoBars' Supply & Demand Zones strategy template category
(https://algobars.com/strategy-templates/supply-demand/ and
https://algobars.com/strategy-templates/supply-demand/drop-base-rally/,
browser_exec fallback after web_search's DuckDuckGo backend returned
empty/error results for multiple queries this iteration). Source's own
disclosed rule set for "Drop-Base-Rally Demand":

    "Drop-Base-Rally (DBR): price drops sharply, consolidates briefly
    (base), then explodes higher. The base marks a fresh demand zone
    where institutional buying absorbed all selling. Fresh DBR zones are
    high-quality bounce levels.
    Rules: Identify Drop-Base-Rally: sharp decline -> 1-6 candle
    consolidation -> sharp advance. Mark zone = high and low of the
    'base' candles. Wait for price to return to this zone later. Zone
    must be FRESH (first touch since formation). Enter long on bullish
    reversal candle at zone. Stop: below zone low. Target: 3:1 R:R
    minimum, or next major resistance.
    Skip if: zone already tested/broken; base has more than 6 candles
    (too much 'memory', probably weak); the rally leg is less than 2x the
    base size (weak demand signal)."

This is a genuinely TWO-PHASE pattern distinct from every prior repo
entry: (1) a ZONE FORMATION phase (decline -> narrow multi-bar
consolidation -> rally >= 2x the consolidation's own range), followed by
(2) a separate, DELAYED retest phase where price must later return to
touch that specific price zone for the FIRST time and show a bullish
reversal bar there. This differs from the already-tested/accepted
Donchian role-reversal retest (2026-09-17-175, single N-day-high
break+immediate retest of a simple high level, no separate consolidation
"base" zone) and from the already-tested/accepted Pothole pattern
(2026-09-24-109, single dip-recovery with no later delayed zone retest
phase at all) -- DBR's core novelty is the explicit zone (a *price band*,
not a single level) formed once and revisited possibly much later.

Adaptation to this repo's contract: this repo's `data/loaders.py` only
supplies daily-bar OHLCV (no true intrabar tick execution and no fixed
"3:1 R:R" order-placement concept -- see SAFETY.md, no order-placement
code). The source's literal "stop below zone low / 3:1 R:R target" is
translated into a zone-height-based measure-rule target (target_rr x zone
height above the zone) and a stop at the zone's own low, both evaluated
on daily closes, plus a max_hold_days time-stop backstop.

Signal logic
------------
1. Zone formation: scan for a `base_window`-bar (<= max_base_bars)
   consolidation window whose own price range (high-low) is small
   relative to the decline that preceded it and the rally that follows
   it. Concretely, for each candidate base end-bar b:
     - decline_ok: close[b - base_window] is at least `decline_pct` below
       the local rolling max close of the `lookback_decline` bars before
       the base (a "sharp decline" into the base).
     - base narrow: (roll_max - roll_min) over the base window, as a
       fraction of roll_min, is <= `base_range_pct` (numeric proxy for a
       narrow 1-6 candle consolidation).
     - rally_ok: within `rally_window` bars after the base ends, price
       rises to at least `rally_mult` x the base's own (high-low) range
       above the base's own high (source's own "rally >= 2x base size"
       filter, generalized to a tunable multiplier).
   Zone = (base_low, base_high) of that base window. Only the most
   recently formed zone is tracked at any time (a fresh simplification of
   the source's "many overlapping zones" full implementation).
2. Retest entry: after zone formation, wait for the FIRST subsequent bar
   where price re-enters the zone (low <= base_high) while the zone has
   not yet been touched before (freshness filter, source's own "zone must
   be FRESH" rule) AND that bar or the following bar is a bullish
   reversal bar (close > open, i.e. a green/bullish candle) at or inside
   the zone. Long entry on that bar's close.
3. Exit: measure-rule target = base_high + target_rr x (base_high -
   base_low), OR close falls below base_low (source's own stop
   location), OR a max_hold_days time-stop, whichever comes first.
4. Skip (not tracked as a fresh zone) if the base itself is wider than
   `max_base_bars` bars or the rally leg does not clear `rally_mult` x
   the base range (source's own two explicit skip conditions).

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
    lookback_decline: int = 15,
    decline_pct: float = 0.05,
    base_window: int = 5,
    max_base_bars: int = 6,
    base_range_pct: float = 0.04,
    rally_window: int = 10,
    rally_mult: float = 2.0,
    target_rr: float = 3.0,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series for DBR zone retest entries."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"] if "open" in df.columns else close
    low = df["low"] if "low" in df.columns else close
    high = df["high"] if "high" in df.columns else close

    close_arr = close.to_numpy()
    open_arr = open_.to_numpy()
    low_arr = low.to_numpy()
    high_arr = high.to_numpy()
    n = len(close_arr)

    base_w = int(max(2, min(base_window, max_base_bars)))

    pre_roll_max = close.rolling(lookback_decline).max().to_numpy()
    base_roll_max_h = pd.Series(high_arr).rolling(base_w).max().to_numpy()
    base_roll_min_l = pd.Series(low_arr).rolling(base_w).min().to_numpy()

    zones = []  # (base_end_idx, base_high, base_low)
    for base_end in range(lookback_decline + base_w, n - 1):
        base_start = base_end - base_w + 1
        pre_idx = base_start - 1
        if pre_idx < 0:
            continue
        pmax = pre_roll_max[pre_idx]
        if np.isnan(pmax) or pmax <= 0:
            continue
        # sharp decline into the base
        if (pmax - close_arr[base_start]) / pmax < decline_pct:
            continue

        b_high = base_roll_max_h[base_end]
        b_low = base_roll_min_l[base_end]
        if np.isnan(b_high) or np.isnan(b_low) or b_low <= 0:
            continue
        base_range = b_high - b_low
        if base_range <= 0:
            continue
        if base_range / b_low > base_range_pct:
            continue  # base not narrow enough

        # rally leg after the base
        rally_end = min(n, base_end + 1 + rally_window)
        if rally_end <= base_end + 1:
            continue
        window_highs = high_arr[base_end + 1: rally_end]
        if len(window_highs) == 0:
            continue
        rally_high = window_highs.max()
        if (rally_high - b_high) < rally_mult * base_range:
            continue  # rally too weak, skip per source's own filter

        zones.append((base_end, b_high, b_low))

    # Retest entries: first FRESH touch of each zone after formation, with
    # a bullish reversal bar (close > open) confirming the bounce.
    entries = {}
    for base_end, b_high, b_low in zones:
        touched = False
        for j in range(base_end + 1, n):
            if touched:
                break
            price_in_zone = low_arr[j] <= b_high and high_arr[j] >= b_low
            if price_in_zone:
                touched = True  # first touch consumes freshness regardless of outcome
                bullish = close_arr[j] > open_arr[j]
                if bullish and j not in entries:
                    height = b_high - b_low
                    target_price = b_high + target_rr * height
                    entries[j] = (target_price, b_low)

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
