"""Strategy: Elastic Volume-Weighted Moving Average (eVWMA) price crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per LuxAlgo's Elastic Volume-weighted MA concept page
(https://www.luxalgo.com/library/concept/elastic-volume-weighted-ma/),
Christian Fries' eVWMA (Technical Analysis of Stocks & Commodities, 2001)
is a recursive average whose smoothing weight on each bar is that bar's
OWN SHARE OF a trailing volume budget N (sum of volume over a lookback
window), rather than a fixed smoothing constant: eVWMA_t = ((N_t - V_t) *
eVWMA_{t-1} + V_t * P_t) / N_t, seeded eVWMA_0 = P_0. High-volume bars pull
the line sharply toward price (acting like a fast average); low-volume
bars barely move it (acting like a slow average) -- it self-regulates
across participation regimes without retuning, unlike a fixed-window
SMA/EMA. Structurally this is a cost-basis reading, closer in spirit to an
anchored VWAP than a fixed-window moving average.

Hypothesis: price closing above/below this participation-adaptive average
signals a trend change with less lag during high-volume (news/breakout)
events than a comparable-speed fixed EMA/SMA, while avoiding whipsaws
during quiet, low-volume drift (since the line barely moves then). Long
entry when close crosses above eVWMA; exit when close crosses back below.

First eVWMA strategy in this repo (zero prior matches for "EVWMA"/"elastic
volume" in strategies_index.jsonl) -- distinct from VWMA (fixed-window
volume-weighted average, already tested multiple times in this repo) and
from Anchored VWAP (session/pivot-anchored cumulative average) since
eVWMA's recursive volume-SHARE weighting has no fixed window boundary and
never fully "forgets" old bars, just discounts them progressively by
volume turnover.

Sources read this iteration:
- https://www.luxalgo.com/library/concept/elastic-volume-weighted-ma/
  (full formula, Fries 2001 origin, participation-adaptive behavior
  description).

Signal logic
------------
- N_t = rolling sum of volume over vol_lookback bars ending at t.
- eVWMA recursively computed per the formula above, seeded at the first
  valid bar with eVWMA_0 = close_0.
- Entry (long): close crosses above eVWMA.
- Exit: close crosses below eVWMA, or a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _evwma(close: pd.Series, volume: pd.Series, vol_lookback: int) -> pd.Series:
    n = len(close)
    rolling_vol_sum = volume.rolling(vol_lookback).sum()
    evwma = pd.Series(index=close.index, dtype=float)

    seeded = False
    prev = None
    for i in range(n):
        Nt = rolling_vol_sum.iloc[i]
        Vt = volume.iloc[i]
        Pt = close.iloc[i]
        if not seeded:
            if pd.notna(Nt) and Nt > 0:
                prev = Pt
                seeded = True
                evwma.iloc[i] = prev
            else:
                evwma.iloc[i] = float("nan")
            continue
        if pd.isna(Nt) or Nt <= 0:
            evwma.iloc[i] = prev
            continue
        prev = ((Nt - Vt) * prev + Vt * Pt) / Nt
        evwma.iloc[i] = prev

    return evwma


def generate_signals(
    price_df: pd.DataFrame,
    vol_lookback: int = 20,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    evwma = _evwma(close, volume, vol_lookback)

    valid = evwma.notna()
    above = (close > evwma) & valid
    above_prev = above.shift(1).fillna(False)
    entry_cross = above & (~above_prev)
    exit_cross = (~above) & above_prev

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0
    for i in range(len(df.index)):
        if not in_position:
            if bool(entry_cross.iloc[i]):
                in_position = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
        else:
            hold_count += 1
            if bool(exit_cross.iloc[i]) or hold_count >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    vol_lookback: int = 20,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(df, vol_lookback=vol_lookback, max_hold_days=max_hold_days)
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
