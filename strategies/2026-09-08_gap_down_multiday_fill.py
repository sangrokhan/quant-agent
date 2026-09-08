"""Strategy: Multi-day-hold Gap-Down Fill (overnight carry until gap closes).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-171):
Per QuantifiedStrategies.com's "How Often Do Overnight Gaps Get Reversed?"
(https://www.quantifiedstrategies.com/how-often-do-overnight-gaps-get-reversed/),
which studied SPY/GLD/TLT since inception: SPY gap-DOWNs get reversed
intraday 52% of the time vs only 35% for gap-UPs -- a meaningful asymmetry
specific to SPY (GLD/TLT show no such bias, ~45-49% both directions). The
article only measures same-day (intraday) reversal, leaving open whether
gaps that do NOT fill same-day continue to mean-revert over the following
days. This strategy tests that extension: instead of the already-rejected
single-day-only gap-down fade (2026-09-08-016, decisive TC-survival fail
from same-day-exit trade frequency), hold the long position across multiple
days (up to max_hold_days) until the gap actually closes (close >= the
pre-gap prior close), rather than forcing a same-day exit. This should cut
trade *frequency* (since not every gap resolves same-day) while keeping the
same underlying asymmetric-reversal edge, addressing 016's exact rejection
reason (78-93 trades/~7.7yr already too thin for costs at higher frequency
-- here we trade less often but hold longer per trade).

Signal logic
------------
- gap_pct[t] = open[t] / close[t-1] - 1
- Entry (long, at day t's open) when gap_pct[t] <= -gap_threshold (a gap
  down of at least gap_threshold, e.g. 0.3%), and we are not already in a
  position.
- Hold long every day after entry (no re-entry while already in a
  position) until EITHER:
    (a) close[t] >= entry-day's prior close (the gap has fully filled), or
    (b) max_hold_days trading days have elapsed since entry (time-stop
        safety backstop, avoiding indefinite holds if the gap never
        fills).
- Flat otherwise. Long-only, no shorting of gap-ups (asymmetry is the
  point of the hypothesis; source only found a directional edge on the
  down side for SPY).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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
    gap_threshold: float = 0.003,
    max_hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    n = len(df)

    prior_close = close.shift(1)
    gap_pct = (open_ / prior_close) - 1.0

    pos = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = -1
    fill_target = np.nan

    gap_arr = gap_pct.values
    close_arr = close.values

    for i in range(n):
        if in_position:
            # Check fill / time-stop -- position is held through today,
            # then closed at the end of today if a condition is met.
            filled = (not np.isnan(fill_target)) and (close_arr[i] >= fill_target)
            timed_out = (i - entry_idx) >= max_hold_days
            pos[i] = 1
            if filled or timed_out:
                in_position = False
                entry_idx = -1
                fill_target = np.nan
            continue

        # Not in a position -- check for a fresh entry today.
        if not np.isnan(gap_arr[i]) and gap_arr[i] <= -gap_threshold:
            in_position = True
            entry_idx = i
            fill_target = close_arr[i - 1] if i > 0 else np.nan
            pos[i] = 1  # enter at today's open, hold through today

    return pd.Series(pos, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    gap_threshold: float = 0.003,
    max_hold_days: int = 5,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    signals = generate_signals(df, gap_threshold=gap_threshold, max_hold_days=max_hold_days)
    # Position held from entry day's open through to exit day's close;
    # approximate entry-day return as open->close move captured via the
    # position being active that day, using the same daily close-to-close
    # return convention as the rest of the repo's strategies (position at
    # t applied to day t's return keeps this consistent/comparable).
    strat_returns = daily_ret * signals.astype(float)
    return strat_returns
