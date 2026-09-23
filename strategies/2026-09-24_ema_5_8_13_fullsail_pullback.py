"""Strategy: 5-8-13 Fibonacci EMA ribbon "Full Sail" pullback-continuation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-015):
Per Stockpathshala's "5 8 13 EMA Crossover Strategy: How It Works in
Trading?" (https://stockpathshala.com/5-8-13-ema-crossover-strategy/):
a 3-EMA ribbon at Fibonacci-spaced periods (5, 8, 13) that achieves "Full
Sail" alignment (EMA5 > EMA8 > EMA13, all rising) signals strong bullish
momentum. The source's own highest-probability entry is NOT the initial
crossover but a pullback to the 8 EMA while Full Sail alignment holds
(price dips to touch/near the 8 EMA and bounces, rather than chasing the
initial cross). Exit ("aggressive" rule, source's own words) when the 5
EMA crosses back below the 8 EMA, signaling early momentum loss. This
repo has zero prior Fibonacci-ribbon (5/8/13) or Guppy-style multi-EMA
entries -- distinct from the many single-pair EMA crossovers already
tested (this uses a 3-line alignment gate PLUS a pullback-to-middle-line
entry trigger, not a simple 2-line cross).

Signal logic
------------
- EMA(5), EMA(8), EMA(13) on close.
- "Full Sail" = EMA5 > EMA8 > EMA13 (source's exact alignment condition).
- Entry (long): Full Sail is active AND close pulls back to touch/dip
  below the EMA8 (within pullback_band_pct of it) on the current or a
  recent bar (checked via a rolling low touching EMA8's band) AND close
  today is back above EMA8 (the "bounce" the source describes) -- i.e. a
  fresh low-then-bounce pattern while the ribbon alignment holds.
- Exit: EMA5 crosses back below EMA8 (source's own "aggressive exit"
  rule), or Full Sail alignment breaks (EMA5 <= EMA8 or EMA8 <= EMA13),
  or a max_hold_days time-stop as a safety net.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    ema_fast: int = 5,
    ema_mid: int = 8,
    ema_slow: int = 13,
    pullback_band_pct: float = 0.005,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]

    e5 = close.ewm(span=ema_fast, adjust=False).mean()
    e8 = close.ewm(span=ema_mid, adjust=False).mean()
    e13 = close.ewm(span=ema_slow, adjust=False).mean()

    full_sail = (e5 > e8) & (e8 > e13)

    # pullback: today's low dips within pullback_band_pct of EMA8 (touches
    # the middle line) while close bounces back above EMA8 on the same bar.
    touched_e8 = low <= e8 * (1 + pullback_band_pct)
    bounced_above = close > e8

    entry = full_sail & touched_e8 & bounced_above

    exit_cross = e5 < e8
    exit_align_break = ~full_sail

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if pd.isna(e13.iloc[i]):
            position.iloc[i] = 0
            continue
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or bool(exit_align_break.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
