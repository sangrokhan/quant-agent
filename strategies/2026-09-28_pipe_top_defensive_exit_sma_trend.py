"""Strategy: SMA trend-following long with a Bulkowski Pipe Top defensive
exit overlay.

Hypothesis (source: https://thepatternsite.com/pipet.html, Thomas
Bulkowski, read 2026-09-28 via browser_exec):

A Pipe Top is a bearish reversal pattern: "twin and adjacent upward
spikes" (two large-range up-thrust bars with closely overlapping highs),
usually forming "at the top of a retrace in a prolonged downtrend" or
after an advance, confirming when "price closes below the lowest price
in the pattern" -- source's own stats: average decline 19%, break-even
failure rate 13%. Since this repo's SAFETY.md scope is long-only, the
natural bearish-reversal short trade isn't available; instead (matching
this repo's existing exit-overlay convention for other bearish patterns
like Wyckoff UTAD, 2026-09-28-006/2026-09-28-wyckoff_utad) this is
operationalized as a DEFENSIVE EXIT overlay on a plain SMA-crossover
trend-following long: a completed/confirmed Pipe Top while already long
triggers an immediate protective exit, on the theory that exiting BEFORE
the pattern's typical post-confirmation decline improves risk-adjusted
returns versus holding through the baseline's own (slower) SMA-cross
exit alone. First "Pipe Top" strategy in this repo (0 prior hits) --
distinct from the already-tested Pipe Bottom (a twin DOWNWARD-spike
bullish-reversal ENTRY signal, 2026-09-24 accepted) both in direction
(bearish vs bullish) and role (exit overlay vs entry trigger).

Signal logic (daily-bar mechanical proxy for the source's twin-spike
rule, matching the sibling Pipe Bottom strategy's spike-detection
scaffolding but inverted for upward spikes):
- Baseline entry: close crosses above SMA(trend_window) (simple trend
  filter, standard repo convention for exit-overlay tests).
- Spike detection: a bar is an upward "spike" if its (high-low) range
  exceeds `spike_atr_mult` times the trailing ATR(14) AND its close is
  in the UPPER `spike_close_pct` fraction of its own bar range (close
  near the high, consistent with an upward thrust).
- Twin-pipe candidate: two ADJACENT spike bars (i-1, i) whose HIGHS are
  within `high_overlap_pct` of each other (source's disclosed small
  variation, widened as a tunable parameter for daily-bar noise).
- Pipe Top confirmation: the first subsequent bar whose close falls
  below the LOWER of the two spike lows (source's own "confirms when
  price closes below the lowest price in the pattern").
- Exit: baseline SMA trend-filter break (close < SMA(trend_window)), OR
  a confirmed Pipe Top while long (defensive exit), OR a max_hold_days
  time-stop -- whichever comes first.

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


def _pipe_top_confirmed(
    df: pd.DataFrame,
    spike_atr_mult: float,
    spike_close_pct: float,
    high_overlap_pct: float,
    confirm_window: int,
) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    atr = _atr(df, 14)
    bar_range = (high - low).replace(0, np.nan)

    is_spike = (bar_range >= spike_atr_mult * atr) & (
        (close - low) / bar_range >= (1 - spike_close_pct)
    )

    n = len(df)
    high_arr = high.to_numpy()
    low_arr = low.to_numpy()
    close_arr = close.to_numpy()
    spike_arr = is_spike.fillna(False).to_numpy()

    confirmed = np.zeros(n, dtype=bool)

    for i in range(1, n):
        if not (spike_arr[i - 1] and spike_arr[i]):
            continue
        h1, h2 = high_arr[i - 1], high_arr[i]
        if h1 <= 0:
            continue
        if abs(h1 - h2) / h1 > high_overlap_pct:
            continue
        pipe_low = min(low_arr[i - 1], low_arr[i])
        for j in range(i, min(i + confirm_window + 1, n)):
            if close_arr[j] < pipe_low:
                confirmed[j] = True
                break

    return pd.Series(confirmed, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    spike_atr_mult: float = 1.8,
    spike_close_pct: float = 0.3,
    high_overlap_pct: float = 0.02,
    confirm_window: int = 5,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    sma = close.rolling(trend_window).mean()
    trend_ok = close > sma
    fresh_entry = trend_ok & (~trend_ok.shift(1).fillna(False))

    pipe_top = _pipe_top_confirmed(
        df, spike_atr_mult, spike_close_pct, high_overlap_pct, confirm_window
    )

    n = len(df)
    trend_ok_arr = trend_ok.to_numpy()
    fresh_entry_arr = fresh_entry.to_numpy()
    pipe_top_arr = pipe_top.to_numpy()

    pos = pd.Series(0.0, index=df.index)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = (
                not bool(trend_ok_arr[i])
                or bool(pipe_top_arr[i])
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
    spike_atr_mult: float = 1.8,
    spike_close_pct: float = 0.3,
    high_overlap_pct: float = 0.02,
    confirm_window: int = 5,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    pos = generate_signals(
        df,
        trend_window=trend_window,
        spike_atr_mult=spike_atr_mult,
        spike_close_pct=spike_close_pct,
        high_overlap_pct=high_overlap_pct,
        confirm_window=confirm_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0.0)
    return strat_ret
