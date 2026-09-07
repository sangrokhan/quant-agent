"""Strategy: OBV pivot-confirmed bullish divergence with independent price confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-048):
Follow-up to already-rejected 2026-09-04-088 (OBV divergence via rolling
N-bar price/OBV extremes, low Sharpe 0.657, only 20 trades over 7.7yr --
too rare). Per chartmini.com's OBV divergence rule methodology
(https://chartmini.com/blog/advanced-on-balance-volume-techniques-for-profitable-trading),
a properly defined divergence needs explicit CONFIRMED PIVOTS (not rolling
N-bar extremes) plus an INDEPENDENT price-action confirmation event distinct
from the divergence itself:
  - Price has a confirmed pivot low P1, then a later confirmed pivot low P2
    that is LOWER than P1 (price making a new low).
  - OBV, at the bars associated with P1/P2, has pivot lows O1 then O2 where
    O2 is HIGHER than O1 (OBV NOT confirming the new price low -- divergence).
  - Confirmation: close breaks back above the swing high between P1 and P2
    (an independent price event, not just an EMA crossback as in -088).
This is a genuinely different pivot-based construction from -088's rolling
N-bar-extreme comparison, testing the source's explicit prescription that
divergence needs pivot-to-pivot comparison + independent confirmation, not
rolling-window extremes + a moving-average crossback.

Signal logic
------------
- Detect local pivot lows in price and OBV using a symmetric left/right
  window (pivot_window bars each side; a bar is a pivot low if it's the min
  of the window centered on it).
- Track the two most recent confirmed price pivot lows P1 (older), P2
  (newer). Bullish divergence candidate when P2 < P1 and the OBV values at
  the same bar indices satisfy O2 > O1.
- Entry (long): once a divergence candidate exists, wait for close to break
  above the highest close between P1's bar and P2's bar (the "swing high"
  confirmation).
- Exit: after max_hold_days trading days, OR close falls back below P2's
  low (invalidation stop).
- Flat (no position) whenever not in an active long.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff().fillna(0.0))
    return (direction * volume.fillna(0.0)).cumsum()


def _pivot_lows(series: pd.Series, window: int) -> np.ndarray:
    """Boolean array: True at bar i if series[i] is the min over [i-window, i+window]."""
    vals = series.values
    n = len(vals)
    is_pivot = np.zeros(n, dtype=bool)
    for i in range(window, n - window):
        seg = vals[i - window : i + window + 1]
        if vals[i] == np.min(seg) and not np.isnan(vals[i]):
            is_pivot[i] = True
    return is_pivot


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(0.0, index=close.index)

    obv = _obv(close, volume)
    price_pivot_low = _pivot_lows(close, pivot_window)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)

    pivot_idxs = np.where(price_pivot_low)[0]

    in_position = False
    entry_idx = 0
    entry_stop_level = -np.inf

    # Track pending divergence candidate: (p1_idx, p2_idx, confirm_level)
    pending = None  # (p1_idx, p2_idx, confirm_close_level, invalidation_level)

    close_vals = close.values
    obv_vals = obv.values

    piv_pointer = 0  # index into pivot_idxs for the "P1" side as we scan forward
    last_two_pivots: list = []

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if close_vals[i] < entry_stop_level or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        # Register any pivot at this bar (pivot detection needs pivot_window
        # bars of lookahead, so a pivot "confirmed" at bar i actually
        # occurred at bar i - pivot_window; we only know it now).
        confirm_bar = i - pivot_window
        if confirm_bar >= 0 and price_pivot_low[confirm_bar]:
            last_two_pivots.append(confirm_bar)
            if len(last_two_pivots) > 2:
                last_two_pivots.pop(0)
            if len(last_two_pivots) == 2:
                p1, p2 = last_two_pivots
                if close_vals[p2] < close_vals[p1] and obv_vals[p2] > obv_vals[p1]:
                    swing_high = np.max(close_vals[p1 : p2 + 1])
                    pending = (p1, p2, swing_high, close_vals[p2])
                else:
                    pending = None

        if pending is not None:
            p1, p2, confirm_level, invalidation_level = pending
            if close_vals[i] < invalidation_level:
                pending = None
            elif close_vals[i] > confirm_level:
                in_position = True
                entry_idx = i
                entry_stop_level = invalidation_level
                position.iloc[i] = 1
                pending = None
                continue

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
