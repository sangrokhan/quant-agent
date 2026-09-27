"""Strategy: Volume Divergence ("fading effort") defensive-exit overlay on
an SMA trend-following long.

Hypothesis (source: https://www.luxalgo.com/library/concept/volume-divergence/,
read 2026-09-28 via browser_exec while browsing LuxAlgo's Volume & Order
Flow library for a fresh angle; the standalone Herrick Payoff Index concept
found the same iteration requires open-interest data this repo's
data/loaders.py (yfinance/ccxt OHLCV) doesn't provide, so it was skipped as
infeasible rather than tested):

LuxAlgo's Volume Divergence concept page describes "fading effort":
successive impulse legs in a trend (higher highs in an advance) fueled by
SHRINKING volume signals that "the move is running out of participants" --
source's own words: "volume sliding lower on each new price extreme is the
divergence." Source's own measurement convention: "Comparing single peak
bars is noisy; summing each leg's volume ... is steadier" -- i.e. compare
the SUMMED volume of two successive same-direction swing legs (identified
via pivot highs), not just single-bar volume readings.

Since this repo is long-only (SAFETY.md), fading-effort divergence into a
NEW HIGH is operationalized as a DEFENSIVE EXIT overlay on top of a plain
SMA-crossover trend-following long baseline -- the same established
long-only-adaptation pattern used for other normally-bearish reversal
signals in this repo (e.g. Wyckoff UTAD 2026-09-28-006, Reverse Elder
Impulse). Zero prior hits for "Volume Divergence" as an actual tested
strategy in strategies_index.jsonl (the one existing entry, 2026-09-21-192,
explicitly declined to test it as "generic, no new numeric rule").

Hypothesis: while long in an SMA-trend-following position, a fresh
swing-pivot high whose fueling-leg summed volume is materially below the
PRIOR swing leg's summed volume (source's "fading effort" signature) warns
that the advance lacks genuine participation and should trigger an
immediate protective exit, pre-empting the stall/reversal that classically
follows fading-effort divergence, rather than waiting for the slower SMA
trend-filter's own exit.

Signal logic (daily-bar mechanical proxy for source's pivot-leg volume
comparison):
- Baseline entry/trend gate: close crosses above SMA(trend_window) (this
  repo's standard exit-overlay-test convention).
- Swing pivots: a local high at bar i if high[i] is the max of the trailing
  `pivot_window` bars (simple rolling-max pivot detector, no lookahead).
- Leg volume: sum of volume from the PREVIOUS confirmed pivot high (or
  start of data) up to and including the current pivot high -- this is the
  "leg" the source refers to.
- Fading-effort divergence confirmed when: today's high is a fresh pivot
  high AND that high exceeds the PRIOR pivot high's price (source's
  "successive higher highs") AND today's leg volume < `fade_ratio` (default
  0.7) times the PRIOR leg's volume (source's "summed leg volume ...
  sliding lower").
- Exit: baseline SMA trend-filter break (close < SMA(trend_window)), OR a
  confirmed fading-effort divergence while long (defensive exit), OR a
  max_hold_days time-stop -- whichever comes first.

Interface contract (see validation/validators.py and validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def _fading_effort_divergence(
    df: pd.DataFrame, pivot_window: int, fade_ratio: float
) -> pd.Series:
    high = df["high"].to_numpy()
    volume = df["volume"].to_numpy()
    n = len(df)

    # Rolling-max pivot high detector: bar i is a pivot high if it's the max
    # of the trailing pivot_window bars (including itself) -- no lookahead.
    rolling_max = df["high"].rolling(pivot_window).max().to_numpy()
    is_pivot = np.zeros(n, dtype=bool)
    for i in range(pivot_window - 1, n):
        if high[i] >= rolling_max[i] and high[i] == np.max(high[max(0, i - pivot_window + 1) : i + 1]):
            is_pivot[i] = True

    divergence = np.zeros(n, dtype=bool)
    prev_pivot_idx = -1
    prev_pivot_high = -np.inf
    prev_leg_vol = None
    leg_start = 0

    for i in range(n):
        if is_pivot[i]:
            leg_vol = volume[leg_start : i + 1].sum()
            if prev_pivot_idx >= 0 and high[i] > prev_pivot_high and prev_leg_vol is not None:
                if leg_vol < fade_ratio * prev_leg_vol:
                    divergence[i] = True
            prev_pivot_idx = i
            prev_pivot_high = high[i]
            prev_leg_vol = leg_vol
            leg_start = i + 1

    return pd.Series(divergence, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    pivot_window: int = 10,
    fade_ratio: float = 0.7,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    sma = close.rolling(trend_window).mean()
    trend_ok = close > sma
    fresh_entry = trend_ok & (~trend_ok.shift(1).fillna(False))

    divergence = _fading_effort_divergence(df, pivot_window, fade_ratio)

    n = len(df)
    trend_ok_arr = trend_ok.to_numpy()
    fresh_entry_arr = fresh_entry.to_numpy()
    divergence_arr = divergence.to_numpy()

    pos = pd.Series(0.0, index=df.index)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = (
                not bool(trend_ok_arr[i])
                or bool(divergence_arr[i])
                or hold_count >= max_hold_days
            )
            if exit_now:
                in_pos = False
                hold_count = 0
            else:
                pos.iloc[i] = 1.0
        if not in_pos and bool(fresh_entry_arr[i]):
            in_pos = True
            hold_count = 0
            pos.iloc[i] = 1.0

    return pos


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    pivot_window: int = 10,
    fade_ratio: float = 0.7,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    pos = generate_signals(
        df,
        trend_window=trend_window,
        pivot_window=pivot_window,
        fade_ratio=fade_ratio,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0.0)
    return strat_ret
