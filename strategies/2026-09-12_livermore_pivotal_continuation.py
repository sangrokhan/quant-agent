"""Strategy: Livermore Pivotal-Point breakout + volume "normal pullback" continuation.

Hypothesis (see knowledge_base id 2026-09-12-168):
Per tradethatswing.com's "Swing Trading Lessons From 'How to Trade in
Stocks' by Jesse Livermore" (https://tradethatswing.com/swing-trading-
lessons-from-how-to-trade-in-stocks-by-jesse-livermore/), Livermore's
"pivotal point" system consists of two mechanically stated pieces:

  1. Pivotal point breakout: "Wait for a breakout from a consolidation or
     pivotal point... Breaks through and runs: trade in that direction,
     hold, or add." Operationalized here as close breaking above the
     rolling N-day high (the "pivotal point" == recent range high).
  2. Volume "normal pullback" continuation sequence (source's own 4-step
     description): "Strong start: a new move begins with unusually high
     volume... Trend follow-through: prices continue... Normal pullback:
     volume contracts and price retraces slightly -- this is healthy, not
     a reversal... Trend confirmation: within several days, volume expands
     again and the original trend resumes." "Exit immediately if the
     pattern breaks and price moves meaningfully against the trend."

Operationalized as a long-only regime-and-trigger strategy, distinct from
this repo's existing 52-week-high / Donchian-breakout / VCP families
(different mechanic: breakout is on a *volume-confirmed* pivotal high, not
a plain price high, and the exit is a volume-and-price "pattern broke"
check rather than a trailing stop or fixed SMA cross):

Signal logic
------------
- Pivotal point: rolling `pivot_window`-day high of `close` (excluding
  today), i.e. the level whose penetration is Livermore's "breakout
  confirmation."
- Entry trigger (Livermore's "strong start"): close breaks above the
  pivotal point AND that day's volume >= `vol_confirm_mult` x its own
  rolling `vol_window`-day average volume (the source's "unusually high
  volume" confirmation -- without this, a breakout is not tradable per
  Livermore's own "never anticipate, wait for volume to confirm" rule).
- While in a position, monitor for the source's own explicit failure
  condition: "Exit immediately if the pattern breaks and price moves
  meaningfully against the trend" -- operationalized as close falling
  below the pivotal breakout level itself (the level is "broken" back
  through) by more than `break_pct` (a de-whipsaw buffer), OR a
  `max_hold_days` time-stop (this repo's standard backstop against
  indefinite holds, since Livermore himself traded discretionarily with no
  fixed time exit).
- No re-entry mid-hold; only new pivotal breakouts re-trigger a fresh long.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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
    pivot_window: int = 40,
    vol_window: int = 20,
    vol_confirm_mult: float = 1.5,
    break_pct: float = 0.02,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]
    n = len(close)

    pivotal_high = close.shift(1).rolling(pivot_window).max()
    avg_volume = volume.shift(1).rolling(vol_window).mean()

    breakout = (close > pivotal_high) & (volume >= vol_confirm_mult * avg_volume)
    breakout = breakout.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    pivot_level = np.nan

    for i in range(n):
        if in_position:
            held = i - entry_idx
            broke_down = (not np.isnan(pivot_level)) and (
                close.iloc[i] < pivot_level * (1.0 - break_pct)
            )
            if broke_down or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                pivot_level = np.nan
                continue
            position.iloc[i] = 1
        else:
            if bool(breakout.iloc[i]):
                in_position = True
                entry_idx = i
                pivot_level = pivotal_high.iloc[i]
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    pivot_window: int = 40,
    vol_window: int = 20,
    vol_confirm_mult: float = 1.5,
    break_pct: float = 0.02,
    max_hold_days: int = 30,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs here)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        pivot_window=pivot_window,
        vol_window=vol_window,
        vol_confirm_mult=vol_confirm_mult,
        break_pct=break_pct,
        max_hold_days=max_hold_days,
    )

    daily_returns = close.pct_change().fillna(0.0)
    # Execution-lag convention: trade on the signal generated at the close
    # of day t, realized as the return of day t+1 (avoid look-ahead bias).
    strat_returns = position.shift(1).fillna(0) * daily_returns
    return strat_returns
