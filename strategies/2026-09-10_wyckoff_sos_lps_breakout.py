"""Strategy: Wyckoff Sign of Strength (SOS) breakout + Last Point of
Support (LPS) pullback entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-006):
Per tradingwyckoff.com's Sign of Strength explainer
(https://tradingwyckoff.com/en/sign-of-strength/): after an accumulation
range, a Sign of Strength (SOS) is a breakout above the range's upper
boundary marked by "expanded ranges, elevated volume, no re-entry to the
range, and significant distance." Critically, the source explicitly
states "this breakout movement itself is not a trading opportunity" --
the actual entry comes on the SUBSEQUENT test/confirmation event (the
Last Point of Support, LPS): a pullback back toward the broken range top
that HOLDS (does not re-enter the range), confirming institutional demand
absorbed the retest.

This is mechanically DISTINCT from this repo's already-tested Wyckoff
Spring strategies (2026-09-09-105/106, both rejected): a Spring is a
FAILED-BREAKDOWN reversal pattern (price probes BELOW the range low then
reclaims it -- a bottoming/accumulation-completion signal). SOS is the
OPPOSITE-direction, opposite-stage pattern: a genuine breakout ABOVE the
range top with volume/range expansion, entered not on the breakout bar
itself but on the confirmed pullback-that-holds afterward (LPS) -- a
trend-CONTINUATION entry after the range has already resolved upward,
not a range-completion reversal entry.

Signal logic
------------
- Consolidation range: over a trailing `range_window` bars, the range
  (rolling max high - rolling min low) must be "tight" relative to price
  (range / midpoint <= `max_range_pct`) -- approximates an accumulation
  range per source's own description of the pattern's prerequisite.
- SOS bar: close breaks above the range's rolling high (`range_window`-day
  max high, computed over the window ending the PRIOR bar so the
  breakout bar itself is outside the lookback), with (a) that day's
  (high-low) range >= `wide_range_mult` x its own `atr_window`-day ATR
  (source: "expanded ranges") and (b) volume >= `vol_mult` x its own
  `vol_window`-day average volume (source: "elevated volume").
- No-re-entry confirmation: for `confirm_days` consecutive bars following
  the SOS bar, close must stay >= the broken range-high level (source:
  "no re-entry to the range" is "the most reliable signal of
  intentionality").
- LPS entry: on the FIRST bar after the no-re-entry confirmation window
  where close pulls back toward (within `lps_tolerance_pct` of) the
  broken range-high level and then recovers (that bar's close > that
  bar's own open, i.e. a bullish bar at the test level) -- the source's
  "test" event confirming demand at the former resistance-now-support
  level. If no such pullback-and-hold occurs within `lps_search_days`
  bars of the confirmation window ending, enter directly on the first
  bar after confirmation instead (a fallback so the strategy still
  trades pure strong breakouts that never pull back).
- Exit: close falls back below the broken range-high level (LPS/support
  failed), OR after `max_hold_days` (avoid indefinite holds).
- Flat otherwise. Long-only.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
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
    range_window: int = 30,
    max_range_pct: float = 0.15,
    atr_window: int = 14,
    wide_range_mult: float = 1.3,
    vol_window: int = 20,
    vol_mult: float = 1.5,
    confirm_days: int = 3,
    lps_tolerance_pct: float = 0.02,
    lps_search_days: int = 10,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)
    n = len(df)

    range_high = high.rolling(range_window).max().shift(1)
    range_low = low.rolling(range_window).min().shift(1)
    range_width_pct = (range_high - range_low) / ((range_high + range_low) / 2.0)

    tr = pd.concat(
        [
            (high - low),
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(atr_window).mean()
    avg_vol = volume.rolling(vol_window).mean()
    day_range = high - low

    close_a = close.values.astype(float)
    open_a = open_.values.astype(float)
    range_high_a = range_high.values.astype(float)
    range_width_pct_a = range_width_pct.values.astype(float)
    day_range_a = day_range.values.astype(float)
    atr_a = atr.values.astype(float)
    vol_a = volume.values.astype(float)
    avg_vol_a = avg_vol.values.astype(float)

    position_a = np.zeros(n, dtype=int)

    in_position = False
    entry_idx = 0
    support_level = None

    # State machine: 0 = idle, searching for SOS bar
    #                1 = confirming no-re-entry
    #                2 = searching for LPS pullback within lps_search_days
    state = 0
    sos_level = None
    confirm_count = 0
    lps_search_count = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            c = close_a[i]
            if c < support_level or held >= max_hold_days:
                in_position = False
                position_a[i] = 0
                state = 0
                continue
            position_a[i] = 1
            continue

        c = close_a[i]
        o = open_a[i]
        rh = range_high_a[i]
        rw = range_width_pct_a[i]

        if state == 0:
            if (
                not np.isnan(rh)
                and not np.isnan(rw)
                and rw <= max_range_pct
                and c > rh
                and not np.isnan(day_range_a[i])
                and not np.isnan(atr_a[i])
                and atr_a[i] > 0
                and day_range_a[i] >= wide_range_mult * atr_a[i]
                and not np.isnan(avg_vol_a[i])
                and avg_vol_a[i] > 0
                and vol_a[i] >= vol_mult * avg_vol_a[i]
            ):
                state = 1
                sos_level = rh
                confirm_count = 0
            position_a[i] = 0
            continue

        if state == 1:
            if c < sos_level:
                # re-entered the range -- failed breakout, abandon
                state = 0
                position_a[i] = 0
                continue
            confirm_count += 1
            if confirm_count >= confirm_days:
                state = 2
                lps_search_count = 0
            position_a[i] = 0
            continue

        if state == 2:
            if c < sos_level:
                state = 0
                position_a[i] = 0
                continue
            lps_search_count += 1
            near_support = abs(c - sos_level) / sos_level <= lps_tolerance_pct
            bullish_bar = c > o
            if near_support and bullish_bar:
                in_position = True
                entry_idx = i
                support_level = sos_level
                position_a[i] = 1
                state = 0
                continue
            if lps_search_count >= lps_search_days:
                # fallback: enter directly, no pullback occurred
                in_position = True
                entry_idx = i
                support_level = sos_level
                position_a[i] = 1
                state = 0
                continue
            position_a[i] = 0
            continue

    return pd.Series(position_a, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
