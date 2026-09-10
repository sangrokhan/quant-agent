"""Strategy: 1-2-3 Reversal pattern (bullish variant) -- neckline breakout after
a swing-low -> pullback-high (neckline) -> higher-low structure.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-022):
Per Google AI-overview synthesis of LuxAlgo/TITAN FX Research Hub/RoboForex/
TradingView 1-2-3-reversal explainers (visited this iteration): the bullish
1-2-3 reversal pattern requires three confirmed swing points, in order:
  Point 1: a swing low marking the end of the prior downtrend (fractal low).
  Point 2: the subsequent swing HIGH of the recovery rally off Point 1 (this
           price level becomes the "neckline"/trigger level).
  Point 3: a secondary pullback swing LOW that holds ABOVE Point 1 (a higher
           low, confirming the downtrend's selling pressure is exhausted).
The pattern is only "confirmed" (tradeable) once price subsequently breaks
back above the Point 2 neckline level -- this is the exact entry trigger
(source's own "Close Rule": the bar must CLOSE beyond Point 2, filtering out
false wick spikes). Stop-loss placement is beyond Point 3 (source's own
rule). This repo also adds a max_hold_days safety time-stop and an optional
profit target at a risk-multiple above entry, since the source's own
"Ross Hook extension" profit-target guidance isn't mechanically disclosed.

Novelty vs existing repo entries: distinct from Turtle Soup / SFP (which are
SINGLE-BAR sweep-and-reject patterns with no neckline breakout confirmation)
and from Island Reversal (a GAP-based pattern) and from the Bulkowski Busted
Pattern strategy (2026-09-11-020, a bounded-magnitude single-support-break
recovery, no three-point swing structure or neckline breakout mechanic).
This is the first THREE-SWING-POINT structural pattern with an explicit
neckline breakout confirmation in this repo.

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


def _fractal_extrema(series: pd.Series, lookback: int, kind: str) -> pd.Series:
    """Confirmed fractal swing extrema (kind='low' or 'high'). series[i] is a
    swing extreme if it's the min/max within [i-lookback, i+lookback]. Only
    known as confirmed once `lookback` bars later have closed."""
    n = len(series)
    is_extreme = pd.Series(False, index=series.index)
    vals = series.values
    for i in range(lookback, n - lookback):
        window = vals[i - lookback : i + lookback + 1]
        center = vals[i]
        if np.isnan(center):
            continue
        if kind == "low":
            if center == np.nanmin(window) and np.sum(window == center) == 1:
                is_extreme.iloc[i] = True
        else:
            if center == np.nanmax(window) and np.sum(window == center) == 1:
                is_extreme.iloc[i] = True
    return is_extreme


def generate_signals(
    price_df: pd.DataFrame,
    fractal_lookback: int = 2,
    max_pattern_bars: int = 40,
    stop_buffer_pct: float = 0.0,
    reward_r_multiple: float = 1.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Scans for a completed Point1(low) -> Point2(high) -> Point3(higher low)
    swing sequence (each point a confirmed fractal extremum), all within
    max_pattern_bars of each other, then enters long at the close of the bar
    that first closes above the Point2 (neckline) price after Point3 is
    confirmed. Stop below Point3 (with an optional buffer), target at
    reward_r_multiple*R above entry, or a max_hold_days time-stop.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close
    n = len(close)

    swing_low_mask = _fractal_extrema(low, fractal_lookback, "low")
    swing_high_mask = _fractal_extrema(high, fractal_lookback, "high")

    low_idxs = list(np.where(swing_low_mask.values)[0])
    high_idxs = list(np.where(swing_high_mask.values)[0])

    position = pd.Series(0, index=close.index, dtype=int)

    # Build a merged, time-ordered list of (bar_idx, confirmation_bar_idx, kind)
    events = []
    for i in low_idxs:
        conf = i + fractal_lookback
        if conf < n:
            events.append((conf, i, "low"))
    for i in high_idxs:
        conf = i + fractal_lookback
        if conf < n:
            events.append((conf, i, "high"))
    events.sort()

    # State machine: look for low(P1) -> high(P2) -> low(P3, higher than P1)
    p1 = None  # (idx, price)
    p2 = None  # (idx, price)
    p3 = None  # (idx, price)
    awaiting_breakout = False

    in_position = False
    entry_i = None
    stop_level = None
    target_level = None

    ev_pointer = 0

    for i in range(n):
        while ev_pointer < len(events) and events[ev_pointer][0] == i:
            _, swing_i, kind = events[ev_pointer]
            ev_pointer += 1
            price_val = low.iloc[swing_i] if kind == "low" else high.iloc[swing_i]

            if kind == "low":
                if p1 is None or not awaiting_breakout:
                    # Either starting fresh, or this is a candidate P3 completing the pattern
                    if p1 is not None and p2 is not None and price_val > p1[1]:
                        # Valid P3: higher low than P1
                        if swing_i - p1[0] <= max_pattern_bars:
                            p3 = (swing_i, price_val)
                            awaiting_breakout = True
                        else:
                            # too far apart -- restart with this as new P1
                            p1 = (swing_i, price_val)
                            p2 = None
                            p3 = None
                            awaiting_breakout = False
                    else:
                        # start a new P1 candidate (reset sequence)
                        p1 = (swing_i, price_val)
                        p2 = None
                        p3 = None
                        awaiting_breakout = False
            else:  # kind == "high"
                if p1 is not None and p2 is None and not awaiting_breakout:
                    if swing_i - p1[0] <= max_pattern_bars:
                        p2 = (swing_i, price_val)
                    # else: stale P1, wait for a new low to restart

        # Check for neckline breakout entry
        if awaiting_breakout and not in_position and p2 is not None and p3 is not None:
            if close.iloc[i] > p2[1]:
                entry_price = close.iloc[i]
                stop_level = p3[1] * (1 - stop_buffer_pct)
                stop_dist = entry_price - stop_level
                if stop_dist <= 0:
                    stop_dist = max(entry_price * 0.01, 1e-6)
                    stop_level = entry_price - stop_dist
                target_level = entry_price + reward_r_multiple * stop_dist
                in_position = True
                entry_i = i
                # reset pattern state -- look for the next one after this trade
                p1 = None
                p2 = None
                p3 = None
                awaiting_breakout = False

        if in_position:
            position.iloc[i] = 1
            price = close.iloc[i]
            hold_len = i - entry_i
            if price <= stop_level or price >= target_level or hold_len >= max_hold_days:
                in_position = False
                entry_i = None
                stop_level = None
                target_level = None

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
