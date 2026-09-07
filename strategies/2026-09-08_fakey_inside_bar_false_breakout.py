"""Strategy: Fakey (Inside Bar false-breakout reversal) pattern.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-069):
The "Fakey" pattern (Nial Fuller price-action methodology): (1) a Mother
Bar establishes a clear high/low range; (2) an Inside Bar forms, fully
contained within the Mother Bar's range (a brief volatility contraction);
(3) price then breaks OUT of the Inside Bar's range (a "false breakout",
often piercing back toward/past the Mother Bar boundary, tempting breakout
traders); (4) price quickly SNAPS BACK and closes back inside the Inside
Bar's original range, invalidating the breakout and trapping the
early breakout entrants. Entry trigger (per priceaction.com): enter in the
DIRECTION OF THE REVERSAL once price closes back inside the Inside Bar's
range after the false break -- for a bullish Fakey (false break below the
IB low, reversal back above it), buy on the reversal close. Stop just
beyond the false-breakout extreme; exit on the reverse signal, price
reclaiming/losing the Mother Bar's opposite boundary, or a max_hold_days
time-stop.

This is the polar OPPOSITE construction to this repo's already-tested
Inside Bar BREAKOUT-CONTINUATION strategy (2026-09-04-090, accepted/
rejected somewhere in the family -- enters on a SUSTAINED breakout beyond
the Mother Bar's high within an expiry window) -- Fakey instead REQUIRES
the initial breakout to FAIL and price to reverse back inside the Inside
Bar's range, making this a mean-reversion/reversal construction using the
identical inside-bar detection primitive but the opposite trigger
condition and trade direction logic.

Source: https://priceaction.com (Nial Fuller Fakey setup); AI-overview
synthesis corroborated by Capital.com, Elirox, AudaCity Capital.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
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
    trend_window: int = 100,
    reversal_window: int = 3,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series (bullish Fakey only)."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close
    n = len(close)

    sma_trend = close.rolling(trend_window).mean()
    uptrend = (close > sma_trend).fillna(False)

    mother_high = high.shift(1)
    mother_low = low.shift(1)
    is_inside_bar = (high <= mother_high) & (low >= mother_low)

    ib_high = high  # inside bar's own high/low IS the range that gets falsely broken
    ib_low = low

    ib_high_arr = ib_high.to_numpy(dtype=float)
    ib_low_arr = ib_low.to_numpy(dtype=float)
    is_ib_arr = is_inside_bar.to_numpy(dtype=bool)
    low_arr = low.to_numpy(dtype=float)
    close_arr = close.to_numpy(dtype=float)
    uptrend_arr = uptrend.to_numpy(dtype=bool)

    position = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = 0.0
    target_recover_level = 0.0

    pending_ib_idx = None  # index of the most recent inside bar awaiting a false-break+reversal

    for i in range(n):
        if is_ib_arr[i]:
            pending_ib_idx = i

        if in_position:
            held = i - entry_idx
            hit_stop = close_arr[i] <= stop_price
            hit_target = close_arr[i] >= target_recover_level
            hit_time = held >= max_hold_days
            if hit_stop or hit_target or hit_time:
                in_position = False
                position[i] = 0
                continue
            position[i] = 1
        else:
            triggered = False
            if pending_ib_idx is not None and i > pending_ib_idx and (i - pending_ib_idx) <= reversal_window:
                ib_low_val = ib_low_arr[pending_ib_idx]
                ib_high_val = ib_high_arr[pending_ib_idx]
                # Bullish Fakey: some bar since the IB broke BELOW the IB
                # low (false break down), and this bar's close reverses
                # back ABOVE the IB low (the reversal-confirmation close),
                # occurring while price is in a broader uptrend.
                false_break_down = low_arr[max(pending_ib_idx + 1, i - reversal_window) : i + 1].min() < ib_low_val if i > pending_ib_idx else False
                reversal_close = close_arr[i] > ib_low_val
                if false_break_down and reversal_close and uptrend_arr[i]:
                    triggered = True
                    stop_price = low_arr[max(pending_ib_idx + 1, i - reversal_window) : i + 1].min() * 0.999
                    target_recover_level = ib_high_val

            if triggered:
                in_position = True
                entry_idx = i
                pending_ib_idx = None
                position[i] = 1
            else:
                position[i] = 0

    return pd.Series(position, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias -- can't trade on today's own close).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
