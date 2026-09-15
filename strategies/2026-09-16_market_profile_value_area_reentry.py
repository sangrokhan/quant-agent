"""Strategy: Market Profile Value Area "80% Rule" re-entry (long-only,
daily-bar analogue).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's
id): per Market Profile / TPO's "80% Rule" (Google AI-overview synthesis
of FTMO/MetroTrade/ThinkMarkets), when price moves outside the established
Value Area (VAH/VAL, the price range containing ~70% of traded volume) and
then re-enters and HOLDS inside for 2 consecutive time periods, there's an
~80% probability of a rotation to the opposite Value Area edge. The
source's own rule uses 30-minute TPO blocks (intraday) -- this repo's
data/loaders.py is daily-bar-only (`load_equity`/`load_crypto` at
interval="1d"), so this is adapted to a DAILY-BAR analogue: the Value Area
is computed from a rolling lookback_n-day volume-weighted price
distribution (VAH/VAL = the price band containing value_area_pct of total
volume, POC = the modal/highest-volume price bin), and "2 consecutive TPO
blocks" becomes "2 consecutive daily closes holding inside the Value Area
after a prior close outside it". Long entry: price was below VAL, then 2
consecutive closes back inside the Value Area (>= VAL) -- profit target
VAH, stop just below the VAL re-entry low.

Sources read this iteration:
- Google AI-overview synthesis of Market Profile TPO "80% Rule" numeric
  entry rules (FTMO, MetroTrade, ThinkMarkets).

First Market Profile / TPO / Value Area strategy in this knowledge base
(zero prior "market profile" matches; this is a deliberate daily-bar
adaptation of an inherently intraday source concept, flagged as such).

Signal logic
------------
- Rolling lookback_n-day window: bin closes into n_bins price buckets
  weighted by volume; VAL/VAH = the narrowest contiguous price band
  containing value_area_pct of total volume around the POC (mode bin).
- Track "outside" state: close < VAL (below) or close > VAH (above).
- Long entry: after >=1 bar below VAL, 2 CONSECUTIVE closes are >= VAL
  (re-entry + hold confirmation) -- entry on the 2nd confirming bar.
- Exit: close >= VAH (target reached) OR close < entry-bar's VAL (stop)
  OR a max_hold_days time-stop.
- Flat otherwise (short side and "re-entry from above VAH" not
  implemented -- long-only per this repo's convention).

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


def _value_area(closes: np.ndarray, volumes: np.ndarray, n_bins: int, value_area_pct: float):
    """Compute (VAL, VAH) for one lookback window via a simple
    volume-weighted histogram + expand-from-POC algorithm (standard
    Market Profile Value Area construction)."""
    lo, hi = closes.min(), closes.max()
    if hi <= lo:
        return lo, hi
    edges = np.linspace(lo, hi, n_bins + 1)
    bin_idx = np.clip(np.digitize(closes, edges) - 1, 0, n_bins - 1)
    vol_per_bin = np.zeros(n_bins)
    for b, v in zip(bin_idx, volumes):
        vol_per_bin[b] += v
    total_vol = vol_per_bin.sum()
    if total_vol <= 0:
        return lo, hi
    poc_bin = int(np.argmax(vol_per_bin))
    included = {poc_bin}
    acc_vol = vol_per_bin[poc_bin]
    lo_b, hi_b = poc_bin, poc_bin
    while acc_vol / total_vol < value_area_pct and (lo_b > 0 or hi_b < n_bins - 1):
        vol_below = vol_per_bin[lo_b - 1] if lo_b > 0 else -1
        vol_above = vol_per_bin[hi_b + 1] if hi_b < n_bins - 1 else -1
        if vol_above >= vol_below:
            hi_b += 1
            acc_vol += vol_per_bin[hi_b]
            included.add(hi_b)
        else:
            lo_b -= 1
            acc_vol += vol_per_bin[lo_b]
            included.add(lo_b)
    val = edges[lo_b]
    vah = edges[hi_b + 1]
    return val, vah


def generate_signals(
    price_df: pd.DataFrame,
    lookback_n: int = 20,
    n_bins: int = 20,
    value_area_pct: float = 0.70,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)

    n = len(df.index)
    val_series = pd.Series(index=df.index, dtype=float)
    vah_series = pd.Series(index=df.index, dtype=float)

    close_np = close.to_numpy()
    vol_np = volume.to_numpy()
    for i in range(lookback_n, n):
        window_closes = close_np[i - lookback_n : i]
        window_vols = vol_np[i - lookback_n : i]
        val, vah = _value_area(window_closes, window_vols, n_bins, value_area_pct)
        val_series.iloc[i] = val
        vah_series.iloc[i] = vah

    position = pd.Series(0, index=df.index, dtype=int)
    was_below = False
    consec_inside = 0
    in_position = False
    hold_days = 0
    entry_val = None

    for i in range(n):
        c = close.iloc[i]
        val = val_series.iloc[i]
        vah = vah_series.iloc[i]

        if in_position:
            hold_days += 1
            if c >= vah or (entry_val is not None and c < entry_val) or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
                entry_val = None
            else:
                position.iloc[i] = 1
                continue

        if pd.isna(val) or pd.isna(vah):
            continue

        if c < val:
            was_below = True
            consec_inside = 0
            continue

        if was_below:
            if c >= val:
                consec_inside += 1
            else:
                consec_inside = 0
            if consec_inside >= 2:
                in_position = True
                hold_days = 1
                entry_val = val
                position.iloc[i] = 1
                was_below = False
                consec_inside = 0
        else:
            consec_inside = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    lookback_n: int = 20,
    n_bins: int = 20,
    value_area_pct: float = 0.70,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_returns = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        lookback_n=lookback_n,
        n_bins=n_bins,
        value_area_pct=value_area_pct,
        max_hold_days=max_hold_days,
    )
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns
