"""Strategy: ZigZag confirmed-pivot trend-continuation breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-091):
Per https://fxglory.com/learn/forex-strategies/forex-zigzag-strategy, a
"repainting-safe" ZigZag only confirms a swing pivot after price has moved
away from it by a chosen percent-deviation threshold -- the article's own
key methodology point is that many ZigZag strategies cheat by trading off
the still-forming (unconfirmed) leg. The source's own "least-negative" of
five tested setups (still net-negative on 1H FX pairs after realistic
spread/slippage costs) was the ZigZag trend-continuation breakout: wait for
confirmed up-structure (each newly confirmed swing high/low higher than the
prior one), then enter long when price breaks above the prior CONFIRMED
swing high; stop beyond the most recent confirmed opposite (low) swing;
here operationalized with a max_hold_days time-stop instead of a fixed R
target (this repo's standard exit convention) since vectorbt-based position
series don't carry per-trade R-multiples directly.

This repo tests the same confirmed-pivot construction on DAILY equity/crypto
bars (very different regime/timeframe/cost structure than the source's 1H
FX test), so the "least-negative but still failed" FX verdict is not
assumed to transfer -- it's tested fresh here per the novelty-check
convention (see strategies_log.jsonl for prior distinct ZigZag/swing-pivot
work, e.g. Andrews Pitchfork 2026-09-06-122, which used a different pivot
construction).

Signal logic
------------
- Percent-deviation ZigZag: track running extreme (high/low) since the last
  confirmed pivot. A pivot is CONFIRMED once price reverses away from that
  running extreme by >= zigzag_pct (e.g. 0.03 = 3%). Confirmation is lagged
  by construction (no lookahead): the confirmed pivot's *value* and *index*
  are known only as of the confirming bar.
- Up-structure: the two most recently confirmed pivots are a low then a
  high, and that confirmed high > the previous confirmed high (higher
  high), and the low that preceded it > the low before that (higher low).
- Entry (long): close breaks above the most recently CONFIRMED swing high
  while in a confirmed up-structure.
- Exit: close breaks below the most recently CONFIRMED swing low (stop,
  mirroring the source's "stop beyond the most recent confirmed opposite
  swing"), or a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _confirmed_pivots(close: pd.Series, zigzag_pct: float):
    """Compute confirmed ZigZag pivots without lookahead.

    Returns two arrays aligned to close.index:
      last_confirmed_high[i]: value of the most recently CONFIRMED swing
        high as of bar i (NaN if none yet).
      last_confirmed_low[i]: value of the most recently CONFIRMED swing
        low as of bar i (NaN if none yet).
      is_up_structure[i]: True if the two most recent confirmed pivots
        (low then high) both represent a higher-high/higher-low vs the
        pivots before them.
    """
    n = len(close)
    last_confirmed_high = [float("nan")] * n
    last_confirmed_low = [float("nan")] * n
    is_up_structure = [False] * n

    # State: running extreme since last confirmed pivot, and direction
    # ("up" = looking for a swing high, "down" = looking for a swing low).
    confirmed_pivots = []  # list of (idx, value, kind) kind in {"high","low"}
    direction = None
    extreme_val = None
    extreme_idx = None

    vals = close.values
    for i in range(n):
        v = vals[i]
        if extreme_val is None:
            extreme_val = v
            extreme_idx = i
            direction = None
        else:
            if direction is None:
                # Not yet committed to a direction; track both.
                if v >= extreme_val:
                    extreme_val = v
                    extreme_idx = i
                # Check reversal from the running max/min tracked so far.
                # Use a simple two-sided bootstrap: if price has moved
                # zigzag_pct away from the extreme in either direction,
                # commit to a direction retroactively.
                if extreme_val and v <= extreme_val * (1 - zigzag_pct):
                    # confirmed a high pivot at extreme_idx
                    confirmed_pivots.append((extreme_idx, extreme_val, "high"))
                    direction = "down"
                    extreme_val = v
                    extreme_idx = i
            elif direction == "up":
                if v > extreme_val:
                    extreme_val = v
                    extreme_idx = i
                elif v <= extreme_val * (1 - zigzag_pct):
                    confirmed_pivots.append((extreme_idx, extreme_val, "high"))
                    direction = "down"
                    extreme_val = v
                    extreme_idx = i
            elif direction == "down":
                if v < extreme_val:
                    extreme_val = v
                    extreme_idx = i
                elif v >= extreme_val * (1 + zigzag_pct):
                    confirmed_pivots.append((extreme_idx, extreme_val, "low"))
                    direction = "up"
                    extreme_val = v
                    extreme_idx = i

        # As of bar i, only pivots confirmed at index <= i are usable.
        # confirmed_pivots is appended at the confirming bar's index j;
        # any pivot in the list has j <= i already since we're iterating
        # forward and only append at the current i.
        highs = [p for p in confirmed_pivots if p[2] == "high"]
        lows = [p for p in confirmed_pivots if p[2] == "low"]
        if highs:
            last_confirmed_high[i] = highs[-1][1]
        if lows:
            last_confirmed_low[i] = lows[-1][1]

        if len(highs) >= 2 and len(lows) >= 2:
            hh = highs[-1][1] > highs[-2][1]
            hl = lows[-1][1] > lows[-2][1]
            is_up_structure[i] = bool(hh and hl)

    return (
        pd.Series(last_confirmed_high, index=close.index),
        pd.Series(last_confirmed_low, index=close.index),
        pd.Series(is_up_structure, index=close.index),
    )


def generate_signals(
    price_df: pd.DataFrame,
    zigzag_pct: float = 0.05,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    last_high, last_low, up_structure = _confirmed_pivots(close, zigzag_pct)

    # Entry trigger: close breaks above the most recent CONFIRMED swing
    # high while in confirmed up-structure. Shift last_high/up_structure by
    # 1 so we only ever compare today's close to pivots confirmed strictly
    # before today (no lookahead through same-bar confirmation).
    prior_high = last_high.shift(1)
    prior_low = last_low.shift(1)
    prior_up_structure = up_structure.shift(1).fillna(False).astype(bool)

    entry = (close > prior_high) & prior_up_structure & prior_high.notna()
    exit_stop = close < prior_low

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_stop.iloc[i]) or held >= max_hold_days:
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
