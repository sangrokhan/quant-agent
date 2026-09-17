"""Strategy: Ehlers Truncated Bandpass Filter (BPT) zero-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-157):
John Ehlers' Traders' Tips article (TASC Jul 2020, "Truncated Indicators",
source: Traders.com Jul 2020 Traders' Tips, TradeStation EasyLanguage code
read this iteration) proposes recomputing a standard IIR (infinite-memory)
2-pole bandpass filter with a forced zero-value boundary condition a fixed
`length` bars back, "truncating" the filter's long-memory recursive tail.
Ehlers' claim is this reduces stale-history artifacts and produces a cleaner,
more current-price-responsive cycle indicator than the standard (untruncated)
bandpass filter. A zero-line crossing of the truncated bandpass value (BPT)
marks a cycle-phase trend shift. First truncated-recursion / bounded-memory
filter strategy in this repo (distinct from all standard IIR/EMA/SuperSmoother
filters already tested, which use infinite recursive memory).

Formula (per source, angles in degrees)
------------------------------------------------------------------------
- L1 = cos(360/period), G1 = cos(bandwidth*360/period)
- S1 = 1/G1 - sqrt(1/G1^2 - 1)
- Truncated recursion (per bar t): initialize Trunc[length+1]=Trunc[length+2]=0,
  then for count = length downto 1:
      Trunc[count] = 0.5*(1-S1)*(Close[count-1] - Close[count+1])
                     + L1*(1+S1)*Trunc[count+1] - S1*Trunc[count+2]
  (Close[n] = close n bars back from t.) BPT(t) = Trunc[1].

Signal logic (long-only adaptation; original also shorts on the bearish
cross, adapted here to repo's long/flat convention)
------------------------------------------------------------------------
- Entry (long): BPT crosses above 0.
- Exit: BPT crosses below 0, OR after `max_hold_days`.
- No short leg.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _truncated_bandpass(close: pd.Series, period: int, bandwidth: float, length: int) -> pd.Series:
    c = close.values
    n = len(c)

    l1 = math.cos(math.radians(360.0 / period))
    g1 = math.cos(math.radians(bandwidth * 360.0 / period))
    inv_g1 = 1.0 / g1
    s1 = inv_g1 - math.sqrt(max(inv_g1 * inv_g1 - 1.0, 0.0))

    bpt = np.zeros(n)

    for t in range(n):
        # need Close[count+1] for count up to length -> offset up to length+1
        if t < length + 1:
            bpt[t] = 0.0
            continue
        # Trunc array indices 1..length+2 (0 = unused), boundary zero at length+1, length+2
        trunc = np.zeros(length + 3)
        for count in range(length, 0, -1):
            close_cm1 = c[t - (count - 1)]  # Close[count-1]
            close_cp1 = c[t - (count + 1)]  # Close[count+1]
            trunc[count] = (
                0.5 * (1 - s1) * (close_cm1 - close_cp1)
                + l1 * (1 + s1) * trunc[count + 1]
                - s1 * trunc[count + 2]
            )
        bpt[t] = trunc[1]

    return pd.Series(bpt, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 20,
    bandwidth: float = 0.1,
    length: int = 10,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    bpt = _truncated_bandpass(close, period, bandwidth, length)

    cross_above = (bpt.shift(1) <= 0) & (bpt > 0)
    cross_below = (bpt.shift(1) >= 0) & (bpt < 0)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    warmup = length + period
    for i in range(len(close)):
        if i < warmup:
            position.iloc[i] = 0
            continue
        if in_position:
            held = i - entry_idx
            if bool(cross_below.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(cross_above.iloc[i]):
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
