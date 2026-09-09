"""Strategy: Rolling Volume Profile Value-Area "failed breakdown" retest/reclaim.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-001):
Per BacktestX's Volume Profile & Order Flow guide
(https://backtestx.in/guide/volume-profile-trading), the "classic
backtesting strategy is the Value Area Retest: if price opens outside the
Value Area but fails to build momentum and returns inside the VAH or VAL,
it is highly likely to travel across the range to target the POC or
opposite boundary."

This is mechanically DISTINCT from the two prior Volume-Profile-family
strategies already tested in this repo:
- 2026-09-04-150 (rejected): unconditional close<=VAL mean reversion,
  single-bar threshold entry, no reclaim confirmation.
- 2026-09-08-129 (accepted, SPY only): VAH breakout CONTINUATION (opposite
  direction thesis -- trades WITH a break above VAH, not against a failed
  break below VAL).

Here the entry requires a two-bar FAILED-BREAKDOWN pattern: yesterday's
close was already below the Value Area Low (an excursion outside "fair
value"), and today's close reclaims back above VAL (the excursion failed
to build momentum) -- only then do we go long, targeting a return to the
POC. This reclaim-confirmation requirement is the source's own stated
rule and is what distinguishes it from the unconditional 2026-09-04-150
threshold entry (which triggered directly on close<=VAL with no
confirmation that the breakdown had already failed).

Signal logic
------------
- Rolling `profile_window`-day window; bin HLC3 into `n_bins` equal-width
  price rows (volume-weighted histogram), same construction as this
  repo's prior two Volume Profile strategies for comparability.
- POC = highest-volume row. Value Area = expand outward from POC,
  greedily adding the richer of the two adjacent unincluded rows, until
  included rows hold >= `va_pct` of total window volume. VAL/VAH = the
  included rows' lower/upper edges.
- Entry (long): yesterday's close < yesterday's VAL (price already
  outside/below the value area) AND today's close >= today's VAL (price
  has reclaimed back inside) -- the "failed breakdown, retest, reclaim"
  pattern.
- Exit: close >= POC (target reached -- price traveled back across the
  range as the source's thesis predicts), OR close falls back below VAL
  again (reclaim failed, renewed breakdown -- stop), OR after
  `max_hold_days` (avoid indefinite holds).
- Flat otherwise. Long-only (long-side reclaim only, mirroring this
  repo's convention of testing the single most literal reading of the
  source's stated rule before adding a symmetric short leg).

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


def _rolling_profile(
    df: pd.DataFrame, profile_window: int, n_bins: int, va_pct: float
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return (poc, val, vah) rolling series computed from a volume histogram."""
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    hlc3 = (df["high"] + df["low"] + df["close"]) / 3.0

    poc = pd.Series(index=close.index, dtype=float)
    val = pd.Series(index=close.index, dtype=float)
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
        included_vol = bin_vol[poc_bin]
        lo, hi = poc_bin, poc_bin
        while included_vol < va_pct * total_vol and (lo > 0 or hi < n_bins - 1):
            vol_above = bin_vol[hi + 1] if hi + 1 < n_bins else -1
            vol_below = bin_vol[lo - 1] if lo > 0 else -1
            if vol_above >= vol_below:
                hi += 1
                included_vol += bin_vol[hi]
            else:
                lo -= 1
                included_vol += bin_vol[lo]
        poc.iloc[i] = (bin_edges[poc_bin] + bin_edges[poc_bin + 1]) / 2.0
        val.iloc[i] = bin_edges[lo]
        vah.iloc[i] = bin_edges[hi + 1]
    return poc, val, vah


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

    poc, val, _vah = _rolling_profile(df, profile_window, n_bins, va_pct)

    was_below_val = close.shift(1) < val.shift(1)
    now_reclaimed = close >= val
    entry = was_below_val.fillna(False) & now_reclaimed.fillna(False)

    target_hit = close >= poc
    renewed_breakdown = close < val

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(target_hit.iloc[i]) or bool(renewed_breakdown.iloc[i]) or held >= max_hold_days:
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
