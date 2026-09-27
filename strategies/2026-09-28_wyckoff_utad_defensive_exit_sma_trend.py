"""Strategy: SMA trend-following long with a Wyckoff UTAD defensive exit overlay.

Hypothesis (source: https://www.luxalgo.com/library/indicator/upthrust-after-distribution/,
read 2026-09-28 via browser_exec while browsing LuxAlgo's indicator library
for a fresh angle -- Demand Index/Trade Volume Index/Pennant already
tested or too structurally complex per strategies_index.jsonl novelty
checks this iteration):

Wyckoff's Upthrust After Distribution (UTAD) is a classic bearish
reversal-confirmation pattern: after a qualified advance (>= 2x ATR over a
lookback), price pauses into an established, boundary-tested trading
range; a LATE breakout above the range's resistance that FAILS BACK INSIDE
within a short failure window is the UTAD -- source's own words: "the
failed terminal break (mature, boundary-tested range, expanded
participation); earlier pokes count as failing rallies, never UTADs." This
is read as strong evidence that distribution (smart-money selling into
the advance) has completed and markdown (a genuine decline) is imminent.

Since this repo's SAFETY.md scope is long-only, we can't short a UTAD
directly. Instead, we operationalize it as a DEFENSIVE EXIT overlay on a
plain SMA-crossover trend-following long baseline (the simplest possible
entry, matching this repo's other exit-overlay-only tests like Elder
SafeZone Stop/Reverse Elder Impulse): a completed UTAD pattern while
already long triggers an immediate protective exit, on the theory that
exiting BEFORE the markdown leg that typically follows a UTAD (source:
"the box resolves bearish") should improve risk-adjusted returns versus
holding through the trend-filter's own (slower) SMA-cross exit alone.

First Wyckoff UTAD strategy in this repo (0 prior hits for "Upthrust After
Distribution"/"UTAD" in strategies_index.jsonl) -- distinct from this
repo's many already-tested Wyckoff-adjacent patterns (Spring/accumulation
range breakouts, Value Area reclaim, generic distribution-range
breakdowns) which all operate on the ACCUMULATION side or via a different
detection mechanism; UTAD is specifically the DISTRIBUTION-top failed-
breakout pattern.

Signal logic (daily-bar mechanical proxy for the source's full structural
detection, since exact swing-pivot/boundary-test geometry needs intraday
tooling this repo's data/loaders.py OHLCV doesn't support):
- Baseline entry: close crosses above SMA(trend_window) (simple trend
  filter, standard repo convention for exit-overlay tests).
- Qualified advance: over the trailing `advance_lookback` bars, the total
  price advance (close - close.shift(advance_lookback)) >=
  `min_advance_atr_mult` * ATR(atr_window).
- Range resistance: rolling max(high) over the trailing
  `range_duration` bars (following the qualified advance).
- UTAD trigger: today's high > range resistance (a break above) but
  today's OR any of the next `failure_window` bars' close falls back
  below that same resistance level (the failed breakout / "upthrust"),
  confirmed by the close-back-below happening within the failure window.
- Exit: baseline SMA trend-filter break (close < SMA(trend_window)), OR
  a completed UTAD pattern while long (defensive exit), OR a
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    prior_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prior_close).abs(),
            (df["low"] - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def _utad_triggered(
    df: pd.DataFrame,
    advance_lookback: int,
    min_advance_atr_mult: float,
    atr_window: int,
    range_duration: int,
    failure_window: int,
) -> pd.Series:
    close = df["close"]
    high = df["high"]
    atr = _atr(df, atr_window)

    advance = close - close.shift(advance_lookback)
    qualified_advance = advance >= min_advance_atr_mult * atr

    resistance = high.rolling(range_duration).max().shift(1)
    breakout = high > resistance

    n = len(df)
    close_arr = close.to_numpy()
    resistance_arr = resistance.to_numpy()
    breakout_arr = breakout.to_numpy()
    qualified_arr = qualified_advance.to_numpy()

    utad = np.zeros(n, dtype=bool)
    for i in range(n):
        if not breakout_arr[i] or not qualified_arr[i] or np.isnan(resistance_arr[i]):
            continue
        for j in range(i, min(i + failure_window + 1, n)):
            if close_arr[j] < resistance_arr[i]:
                utad[j] = True  # UTAD confirms on the failure-back-inside bar
                break

    return pd.Series(utad, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    advance_lookback: int = 50,
    min_advance_atr_mult: float = 2.0,
    atr_window: int = 14,
    range_duration: int = 15,
    failure_window: int = 5,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    sma = close.rolling(trend_window).mean()
    trend_ok = close > sma
    fresh_entry = trend_ok & (~trend_ok.shift(1).fillna(False))

    utad = _utad_triggered(
        df, advance_lookback, min_advance_atr_mult, atr_window, range_duration, failure_window
    )

    n = len(df)
    trend_ok_arr = trend_ok.to_numpy()
    fresh_entry_arr = fresh_entry.to_numpy()
    utad_arr = utad.to_numpy()

    pos = pd.Series(0.0, index=df.index)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = (
                not bool(trend_ok_arr[i])
                or bool(utad_arr[i])
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
    advance_lookback: int = 50,
    min_advance_atr_mult: float = 2.0,
    atr_window: int = 14,
    range_duration: int = 15,
    failure_window: int = 5,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    pos = generate_signals(
        df,
        trend_window=trend_window,
        advance_lookback=advance_lookback,
        min_advance_atr_mult=min_advance_atr_mult,
        atr_window=atr_window,
        range_duration=range_duration,
        failure_window=failure_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0.0)
    return strat_ret
