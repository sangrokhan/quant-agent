"""Strategy: William O'Neil Follow-Through Day (FTD) market-timing entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-067):
Per TraderLion's "What is the Follow Through Day?" article (O'Neil's
CANSLIM market-timing system): after a market correction, a "rally
attempt" begins on the first day the index closes higher following a new
correction-phase low (day 1 of the attempted rally). A "Follow-Through
Day" (FTD) occurs on the attempt's 4th-to-7th trading day when the index
posts a gain of >= ftd_gain_pct (source: modern standard 1.5-2%, using
1.5% here) on volume higher than the prior day -- confirming institutional
buying and a likely durable new uptrend; go long on the FTD's close.
Exit on a "distribution day" cluster (source: multiple down days >=
distribution_day_decline_pct on higher volume within a rolling window
signal renewed institutional selling and a likely failed rally) or a
max_hold_days time-stop as a safety backstop (the source itself notes FTDs
can fail, particularly if distribution appears within the first few days
after the signal).

Operationalized on daily bars (single-index proxy, no cross-sectional
breadth data required, unlike the already-rejected-at-feasibility
McClellan Oscillator/TRIN strategies which need exchange-wide advance/
decline data): rally attempt = first close above the prior close following
a new rolling correction_lookback-day low; FTD = index gain >= ftd_gain_pct
on volume > prior day's volume, occurring on trading day 4-7 of the
attempt (inclusive); distribution day = close down >= distribution_day_
decline_pct on volume > prior day's volume.

First O'Neil-style market-timing (rally-attempt/follow-through-day/
distribution-day state machine) strategy in this repo -- distinct from
every prior single-indicator technical construction and from the already-
rejected Cup-and-Handle chart pattern (2026-09-06-172, a stock-selection
pattern, not a market-timing signal).

Source: https://traderlion.com/trading-strategies/follow-through-day/

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
    correction_lookback: int = 20,
    ftd_gain_pct: float = 0.015,
    ftd_min_day: int = 4,
    ftd_max_day: int = 7,
    distribution_day_decline_pct: float = 0.002,
    distribution_count_threshold: int = 4,
    distribution_window: int = 25,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    if "volume" in df.columns:
        volume = df["volume"]
    else:
        volume = pd.Series(1.0, index=close.index)
    n = len(close)

    c = close.to_numpy(dtype=float)
    v = volume.to_numpy(dtype=float)
    rolling_low = close.rolling(correction_lookback).min().to_numpy(dtype=float)

    daily_ret = np.zeros(n)
    daily_ret[1:] = (c[1:] - c[:-1]) / c[:-1]

    is_new_low = np.zeros(n, dtype=bool)
    for i in range(correction_lookback, n):
        # a new correction-phase low: today's close is the lowest close of
        # the trailing window (using the window ending at i, prior to today
        # being included, i.e. today sets a fresh low vs the prior window).
        is_new_low[i] = c[i] <= rolling_low[i - 1] if i >= 1 else False

    is_distribution_day = np.zeros(n, dtype=bool)
    for i in range(1, n):
        is_distribution_day[i] = (daily_ret[i] <= -distribution_day_decline_pct) and (v[i] > v[i - 1])

    position = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0

    # Rally-attempt state machine.
    rally_day1_idx = None  # index of the day-1 rally-attempt close
    last_low_idx = None

    for i in range(correction_lookback, n):
        if is_new_low[i]:
            last_low_idx = i
            rally_day1_idx = None  # reset: correction continuing / new low resets the attempt

        # Day 1 of a rally attempt: first up-close after the most recent
        # new low, provided no rally attempt is already in progress.
        if (
            rally_day1_idx is None
            and last_low_idx is not None
            and i > last_low_idx
            and daily_ret[i] > 0
        ):
            rally_day1_idx = i

        if in_position:
            held = i - entry_idx
            # count distribution days within the trailing window
            win_start = max(0, i - distribution_window + 1)
            dist_count = int(is_distribution_day[win_start : i + 1].sum())
            if dist_count >= distribution_count_threshold or held >= max_hold_days:
                in_position = False
                position[i] = 0
                continue
            position[i] = 1
        else:
            if rally_day1_idx is not None:
                attempt_day = i - rally_day1_idx + 1  # day 1 = rally_day1_idx itself
                if (
                    ftd_min_day <= attempt_day <= ftd_max_day
                    and daily_ret[i] >= ftd_gain_pct
                    and v[i] > v[i - 1]
                ):
                    in_position = True
                    entry_idx = i
                    position[i] = 1
                else:
                    position[i] = 0
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
