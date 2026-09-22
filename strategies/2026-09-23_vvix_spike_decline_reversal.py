"""Strategy: VVIX extreme-spike-and-decline reversal signal for SPY.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Per https://tosindicators.com/research/using-the-vvix-to-trade-spy (visited
this iteration), the VVIX ("volatility of volatility", expected 30-day
volatility of the VIX itself, published by CBOE) provides a specific
three-part reversal signal for SPY, distinct from this repo's one existing
VVIX entry (2026-09-10-042, a VVIX/VIX-RATIO-vs-its-own-SMA regime gate on
top of an SMA trend-following signal):

  1. VVIX spikes above an extreme threshold (source's disclosed level: 120).
  2. VVIX then DECLINES from that spike (source: "the VVIX often collapses
     within days even if the VIX remains elevated" -- fast mean-reversion
     of VVIX itself, ahead of the underlying VIX/SPY move).
  3. (Source's 3rd confirmation, SPY holding support/bullish candlestick,
     is dropped here as too subjective/pattern-based to encode mechanically
     -- instead this strategy tests the VVIX spike-and-decline signal on
     its own, as the source's central testable claim.)

Source's own historical narrative examples (Feb 2018 Volmageddon, Dec 2018
Fed pause, Mar 2020 COVID low) all describe VVIX peaking and beginning to
decline BEFORE SPY found its bottom -- i.e. the VVIX decline-from-spike is
itself the entry trigger, not a lagging confirmation.

This is a first-time ABSOLUTE-LEVEL-THRESHOLD-based VVIX strategy in this
repo (2026-09-10-042 used a relative VVIX/VIX ratio vs its own trailing
mean, never an absolute VVIX level).

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import sys
import os

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_vvix(idx: pd.DatetimeIndex) -> pd.Series:
    """Fetch VVIX daily closes and align onto the target index (ffill)."""
    from loaders import load_equity

    start = idx.min() - pd.Timedelta(days=30)
    end = idx.max() + pd.Timedelta(days=2)
    vvix_df = load_equity("^VVIX", start.to_pydatetime(), end.to_pydatetime())
    vvix_df = _prep(vvix_df)
    vvix_close = vvix_df["close"]

    vvix_by_date = vvix_close.copy()
    vvix_by_date.index = vvix_by_date.index.normalize()
    vvix_by_date = vvix_by_date[~vvix_by_date.index.duplicated(keep="last")]

    target_dates = idx.normalize()
    aligned = vvix_by_date.reindex(target_dates).ffill()
    aligned.index = idx
    return aligned


def generate_signals(
    price_df: pd.DataFrame,
    spike_threshold: float = 120.0,
    decline_lookback: int = 3,
    normal_threshold: float = 95.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: VVIX made a new local peak (rolling max over `decline_lookback`
    days) above `spike_threshold` within the last `decline_lookback` days,
    AND today's VVIX is below that peak (i.e. VVIX has started declining
    from its spike -- "collapses within days" per source).
    Exit: VVIX falls back to/below `normal_threshold` (source's disclosed
    historical-average range 85-90, using 95 as a conservative "back to
    normal" cutoff), or a max_hold_days time-stop.
    """
    df = _prep(price_df)
    close = df["close"]
    vvix = _get_vvix(df.index)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)

    rolling_peak = vvix.rolling(decline_lookback, min_periods=1).max()
    was_spike = rolling_peak.shift(1) >= spike_threshold
    declining_now = vvix < rolling_peak.shift(1)

    entry_signal = (was_spike & declining_now).fillna(False)

    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            v = vvix.iloc[i]
            if (pd.notna(v) and v <= normal_threshold) or held >= max_hold_days:
                in_position = False
        else:
            if entry_signal.iloc[i]:
                in_position = True
                entry_idx = i
        position.iloc[i] = 1 if in_position else 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    spike_threshold: float = 120.0,
    decline_lookback: int = 3,
    normal_threshold: float = 95.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Daily strategy returns: position(t-1) * price_return(t) (no lookahead)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        spike_threshold=spike_threshold,
        decline_lookback=decline_lookback,
        normal_threshold=normal_threshold,
        max_hold_days=max_hold_days,
    )
    price_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(float) * price_returns
    return strat_returns
