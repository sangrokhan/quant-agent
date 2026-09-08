"""Strategy: Rolling Volume Profile Value-Area-High (VAH) breakout continuation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-129):
Per LuxAlgo's Volume Profile concept explainer (https://www.luxalgo.com/library/concept/volume-profile/),
a rolling N-day volume profile bins traded volume by price to find the
Point of Control (POC, highest-volume price) and a Value Area (VA, the
narrowest band around the POC containing `p`% of the window's total
volume; VAH/VAL = its upper/lower edges). Price breaking decisively above
the VAH (out of the "accepted"/heavily-traded price zone into a
low-volume "rejection" shelf above it) signals the market moving into new
territory with an air pocket / low resistance above -- a breakout
continuation entry, per the concept's own description that "low-volume
shelves between nodes are where price tends to travel fastest."

This is the DIRECT OPPOSITE-DIRECTION construction from the already-tested
Volume Profile POC/VA mean-reversion strategy in this repo
(2026-09-04-150: long entry when close <= VAL, targeting POC) -- here the
economic thesis is trend-continuation breakout above VAH rather than
mean-reversion buy-the-dip at VAL, using the identical rolling
volume-profile construction so any edge difference is attributable purely
to entry-direction/thesis, not to a different indicator.

Signal logic
------------
- Rolling `profile_window`-day window; bin HLC3 (representative bar price)
  into `n_bins` equal-width price rows spanning that window's low/high, with
  each bar's volume assigned entirely to the row containing its HLC3 (a
  standard daily-bar simplification of true intrabar volume distribution,
  consistent with 2026-09-04-150's own approach in this repo).
- POC = row with max volume. Value area = expand outward from the POC row,
  each step adding whichever of the next unincluded row above/below has
  more volume, until included rows hold >= `va_pct` of the window's total
  volume (LuxAlgo's "two-rows-at-a-time" method simplified to one-row-at-
  a-time for a daily-bar coarse profile). VAH = top edge of included rows.
- Entry (long): close crosses from at/below VAH to strictly above VAH
  (fresh breakout, not already-extended).
- Exit: close falls back below VAH (breakout failed/reabsorbed), OR after
  `max_hold_days` (avoid indefinite holds).
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
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


def _rolling_vah(df: pd.DataFrame, profile_window: int, n_bins: int, va_pct: float) -> pd.Series:
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    hlc3 = (df["high"] + df["low"] + df["close"]) / 3.0

    vah = pd.Series(index=close.index, dtype=float)
    for i in range(len(df)):
        if i < profile_window - 1:
            continue
        window_slice = slice(i - profile_window + 1, i + 1)
        w_hlc3 = hlc3.iloc[window_slice].values
        w_vol = volume.iloc[window_slice].values
        w_low = low.iloc[window_slice].values.min()
        w_high = high.iloc[window_slice].values.max()
        if not np.isfinite(w_low) or not np.isfinite(w_high) or w_high <= w_low:
            continue
        bin_edges = np.linspace(w_low, w_high, n_bins + 1)
        bin_idx = np.clip(np.digitize(w_hlc3, bin_edges) - 1, 0, n_bins - 1)
        bin_vol = np.zeros(n_bins)
        for b, v in zip(bin_idx, w_vol):
            bin_vol[b] += v
        total_vol = bin_vol.sum()
        if total_vol <= 0:
            continue
        poc_bin = int(np.argmax(bin_vol))
        included = {poc_bin}
        included_vol = bin_vol[poc_bin]
        lo, hi = poc_bin, poc_bin
        while included_vol < va_pct * total_vol and (lo > 0 or hi < n_bins - 1):
            vol_above = bin_vol[hi + 1] if hi + 1 < n_bins else -1
            vol_below = bin_vol[lo - 1] if lo > 0 else -1
            if vol_above >= vol_below:
                hi += 1
                included.add(hi)
                included_vol += bin_vol[hi]
            else:
                lo -= 1
                included.add(lo)
                included_vol += bin_vol[lo]
        vah_price = bin_edges[hi + 1]
        vah.iloc[i] = vah_price
    return vah


def generate_signals(
    price_df: pd.DataFrame,
    profile_window: int = 20,
    n_bins: int = 12,
    va_pct: float = 0.70,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    vah = _rolling_vah(df, profile_window, n_bins, va_pct)

    was_at_or_below = close.shift(1) <= vah.shift(1)
    now_above = close > vah
    entry = was_at_or_below.fillna(False) & now_above.fillna(False)

    exit_below_vah = close < vah

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_below_vah.iloc[i]) or held >= max_hold_days:
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
