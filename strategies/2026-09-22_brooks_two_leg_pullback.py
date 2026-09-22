"""Strategy: Al Brooks Two-Leg Pullback re-entry (uptrend, second-leg
completion near EMA20).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-XXX):
Source: https://algobars.com/strategy-templates/al-brooks/brooks-2leg-pullback/
(accessed 2026-09-22, browser_exec after web_extract ddgs-backend refused
extraction). Al Brooks' "most pullbacks in a trend have two legs" concept:
in a confirmed uptrend, price commonly pulls back in TWO separate
down-legs (two pushes against the trend) before resuming; the completion
of the SECOND leg -- when it reaches or slightly overshoots the EMA(20) --
offers the highest-probability re-entry point, confirmed by a bullish
signal bar (reversal candle) at that second-leg low. Stop below the signal
bar's low.

First Two-Leg Pullback strategy in this repo (0 prior KB hits for "two-leg
pullback"/"second leg"/"two-push") -- distinct from this repo's other
EMA-pullback constructions (e.g. TEMA pullback-reentry 2026-09-08-056,
single-touch) via requiring the specific TWO-SEQUENTIAL-SWING-LOW
structure (leg 1 down, partial bounce, leg 2 down to/near EMA) rather than
a single touch-and-bounce.

Signal logic (daily bars)
--------------------------
- Uptrend confirmation: close > SMA(trend_window) (approximating Brooks'
  "confirmed uptrend, higher highs/lows").
- Swing pivots via the same rolling `pivot_window`-bar local-extremum test
  used by this repo's other price-action/Elliott/harmonic strategies.
- Leg 1: a swing high (recent trend peak) followed by a swing low (first
  pullback leg's bottom).
- Leg 2: a subsequent partial bounce (swing high, lower than the trend
  peak) followed by a SECOND swing low that is close to or slightly below
  EMA(20) (within `ema_proximity_pct` of the EMA value) -- Brooks' "reaches
  or slightly overshoots EMA 20".
- Entry (long): on the bar of/immediately after the second leg's swing low,
  confirmed by a bullish signal bar (close > open).
- Exit: close reaches a new high beyond the trend peak (measured target,
  approximating Brooks' expectation of trend resumption), OR close falls
  below the second leg's low (stop, source's explicit "stop below the
  signal bar low"), OR a `max_hold_days` time-stop.
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


def _find_pivots(high: pd.Series, low: pd.Series, window: int):
    n = len(high)
    high_arr = high.to_numpy()
    low_arr = low.to_numpy()
    is_swing_high = np.zeros(n, dtype=bool)
    is_swing_low = np.zeros(n, dtype=bool)
    for i in range(window, n - window):
        seg_high = high_arr[i - window : i + window + 1]
        seg_low = low_arr[i - window : i + window + 1]
        if high_arr[i] == seg_high.max():
            is_swing_high[i] = True
        if low_arr[i] == seg_low.min():
            is_swing_low[i] = True
    return is_swing_high, is_swing_low


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 4,
    trend_window: int = 50,
    ema_window: int = 20,
    ema_proximity_pct: float = 0.02,
    max_hold_days: int = 30,
) -> pd.Series:
    df = _prep(price_df)
    high, low, close, open_ = df["high"], df["low"], df["close"], df["open"]

    is_swing_high, is_swing_low = _find_pivots(high, low, pivot_window)
    trend_sma = close.rolling(trend_window).mean()
    ema = close.ewm(span=ema_window, adjust=False).mean()
    uptrend = (close > trend_sma).fillna(False)

    n = len(df)
    high_arr = high.to_numpy()
    low_arr = low.to_numpy()
    close_arr = close.to_numpy()
    open_arr = open_.to_numpy()
    ema_arr = ema.to_numpy()
    uptrend_arr = uptrend.to_numpy()

    pos_arr = [0] * n
    in_pos = False
    hold_days = 0
    entry_stop = None
    entry_target = None

    # State machine: trend_peak -> leg1_low -> leg1_bounce_high -> leg2_low
    state = "await_peak"
    trend_peak = None
    leg1_low = None

    for i in range(n):
        if in_pos:
            hold_days += 1
            hit_target = (entry_target is not None) and close_arr[i] >= entry_target
            hit_stop = (entry_stop is not None) and close_arr[i] < entry_stop
            if hit_target or hit_stop or hold_days >= max_hold_days:
                in_pos = False
                pos_arr[i] = 0
                hold_days = 0
            else:
                pos_arr[i] = 1
            continue

        if not uptrend_arr[i]:
            # Reset the wave count if trend breaks.
            state = "await_peak"
            trend_peak = None
            leg1_low = None
            pos_arr[i] = 0
            continue

        if is_swing_high[i]:
            if state == "await_peak":
                trend_peak = high_arr[i]
                state = "await_leg1_low"
            elif state == "await_leg2_low" and trend_peak is not None:
                # A new higher peak while awaiting leg2 -- treat as trend
                # continuation, reset to a fresh peak.
                if high_arr[i] > trend_peak:
                    trend_peak = high_arr[i]
                    leg1_low = None
                    state = "await_leg1_low"
                # else: a lower bounce high -- stay in await_leg2_low,
                # this becomes the "leg1_bounce_high" implicitly (we don't
                # need to track it explicitly since leg2's low is what
                # matters next).

        if is_swing_low[i]:
            if state == "await_leg1_low":
                leg1_low = low_arr[i]
                state = "await_leg2_low"
            elif state == "await_leg2_low" and leg1_low is not None:
                leg2_low = low_arr[i]
                near_ema = abs(leg2_low - ema_arr[i]) / ema_arr[i] <= ema_proximity_pct if ema_arr[i] else False
                overshoot_ema = leg2_low <= ema_arr[i]
                if (near_ema or overshoot_ema) and leg2_low < leg1_low:
                    # Valid second leg: lower than leg1's low, near/below EMA.
                    # Look for bullish signal bar confirmation at this bar
                    # or check right now if this bar itself is bullish.
                    if close_arr[i] > open_arr[i]:
                        in_pos = True
                        hold_days = 0
                        entry_stop = leg2_low
                        entry_target = trend_peak
                        pos_arr[i] = 1
                        state = "await_peak"
                        trend_peak = None
                        leg1_low = None
                        continue
                    # else: keep waiting for a bullish confirmation bar;
                    # reset leg1_low to this new (deeper) low so a further
                    # leg is measured against it.
                    leg1_low = leg2_low

        pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    pivot_window: int = 4,
    trend_window: int = 50,
    ema_window: int = 20,
    ema_proximity_pct: float = 0.02,
    max_hold_days: int = 30,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        pivot_window=pivot_window,
        trend_window=trend_window,
        ema_window=ema_window,
        ema_proximity_pct=ema_proximity_pct,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
