"""Strategy: Volume-confirmed Darvas Box with SMA trend filter and staircase trailing stop.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Per https://arongroups.co/forex-articles/darvas-boxes-strategy (Abe Cofnas,
"How Traders Use Darvas Boxes to Capture Market Breakouts", visited this
iteration), the ORIGINAL Darvas mechanic (box = new N-day high + confirm_days
of non-exceedance, top/bottom frozen -- already implemented and TESTED in
this repo at strategies/2026-09-05_darvas_box_breakout.py, id=2026-09-05-054,
accepted for equity QQQ/SPY but DECISIVELY rejected for crypto, 0/72 grid
cells) is explicitly described by this source with two additional mechanical
filters the original repo strategy did NOT implement:

  1. Volume confirmation on the breakout candle: "a valid Darvas box
     breakout should show volume at least 1.5 times the 20-session average
     on the breakout candle" -- low-volume breaks are "frequently faded by
     the market and result in false signals". This source claims this is
     the single most important secondary filter, and is a plausible
     specific fix for exactly the false-breakout whipsaw problem that would
     explain a decisive crypto (high-noise, high-volume-variance) rejection.
  2. Momentum/trend alignment check: "is the instrument above its 50-session
     moving average? If yes, the breakout is aligned with the broader
     trend." -- an explicit SMA50 trend gate on top of the breakout signal.
  3. Staircase trailing stop: "As price rises and forms a new box, the stop
     is raised to the bottom of the new box" -- rather than the original's
     fixed max_hold_days time-stop, this source's stop is dynamic: it
     ratchets up to each successively higher confirmed box bottom and only
     exits on a close below the CURRENT (most recent) box's bottom, never
     retreating.

This iteration implements all three additions (volume filter, SMA trend
gate, staircase trailing stop replacing fixed time-stop) on top of the
identical box-formation state machine from 2026-09-05_darvas_box_breakout.py,
and tests specifically whether these fixes rescue the crypto asset class
while preserving (or improving) the existing equity accept. Distinct from
2026-09-05-054: adds volume_mult filter, sma_window trend gate, and replaces
max_hold_days time-stop with a dynamic staircase trailing stop tied to
re-forming box bottoms (mechanically new -- 2026-09-05-054 used a static
box-bottom stop only within the SAME box, plus an unrelated fixed time-stop).

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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
    high_lookback: int = 52,
    confirm_days: int = 3,
    volume_mult: float = 1.5,
    volume_lookback: int = 20,
    sma_window: int = 50,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Mechanics:
      - Box formation state machine identical to 2026-09-05-054: a candidate
        new `high_lookback`-day high must go `confirm_days` consecutive
        sessions without being exceeded to confirm a box (top=triggering
        high, bottom=lowest low over the confirmation window).
      - Entry (breakout) requires ALL of:
          (a) close breaks above the confirmed box top,
          (b) breakout-candle volume >= volume_mult * rolling
              volume_lookback-day average volume (source's 1.5x/20-session
              rule),
          (c) close > SMA(sma_window) (source's "above 50-session MA" trend
              alignment check).
      - Exit: close breaches the CURRENT box's bottom. If price makes a new
        confirmed higher box while already in position, the stop trails up
        to that new box's bottom (staircase trailing stop, per source) --
        implemented by simply always exiting on close < latest confirmed
        box_bottom, and updating box_bottom whenever a new box confirms
        while in position (monotonic: never lowered).
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)
    n = len(close)

    rolling_high = high.rolling(high_lookback).max()
    avg_volume = volume.rolling(volume_lookback).mean()
    sma = close.rolling(sma_window).mean()

    position = pd.Series(0, index=close.index, dtype=int)

    box_top = None
    box_bottom = None
    box_pending_high_idx = None
    confirm_count = 0
    in_position = False

    for i in range(n):
        # --- box (re)formation state machine (same as 2026-09-05-054) ---
        if box_pending_high_idx is not None:
            if float(high.iloc[i]) > float(high.iloc[box_pending_high_idx]):
                box_pending_high_idx = i
                confirm_count = 0
            else:
                confirm_count += 1
                if confirm_count >= confirm_days:
                    box_top = float(high.iloc[box_pending_high_idx])
                    lo_slice = low.iloc[box_pending_high_idx : i + 1]
                    new_bottom = float(lo_slice.min())
                    # staircase trailing stop: only raise the bottom, never lower it
                    if box_bottom is None or new_bottom > box_bottom:
                        box_bottom = new_bottom
                    box_pending_high_idx = None
                    confirm_count = 0

        rh = rolling_high.iloc[i]
        if pd.notna(rh) and float(high.iloc[i]) >= float(rh):
            if box_pending_high_idx is None:
                box_pending_high_idx = i
                confirm_count = 0

        # --- entry/exit logic ---
        if in_position:
            if box_bottom is not None and float(close.iloc[i]) < box_bottom:
                in_position = False
        else:
            if box_top is not None and float(close.iloc[i]) > box_top:
                av = avg_volume.iloc[i]
                sm = sma.iloc[i]
                vol_ok = pd.notna(av) and av > 0 and float(volume.iloc[i]) >= volume_mult * float(av)
                trend_ok = pd.notna(sm) and float(close.iloc[i]) > float(sm)
                if vol_ok and trend_ok:
                    in_position = True

        position.iloc[i] = 1 if in_position else 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    high_lookback: int = 52,
    confirm_days: int = 3,
    volume_mult: float = 1.5,
    volume_lookback: int = 20,
    sma_window: int = 50,
) -> pd.Series:
    """Daily strategy returns: position(t-1) * price_return(t) (no lookahead)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        high_lookback=high_lookback,
        confirm_days=confirm_days,
        volume_mult=volume_mult,
        volume_lookback=volume_lookback,
        sma_window=sma_window,
    )
    price_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(float) * price_returns
    return strat_returns
