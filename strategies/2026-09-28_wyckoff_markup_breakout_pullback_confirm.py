"""Strategy: Markup-phase breakout confirmation (long-only), per LuxAlgo's
Wyckoff "Markup & Markdown" indicator concept.

Hypothesis (source: https://www.luxalgo.com/library/indicator/markup-and-markdown/,
read 2026-09-28 via browser_exec while browsing LuxAlgo's indicator library
for a fresh angle -- Retest & Break Setup / ROC-of-ROC also fresh but this
angle chosen as the most directly testable with a clean long-only mapping):

LuxAlgo's "Markup & Markdown" dates the Wyckoff cycle's two trending phases
with an explicit confirmation discipline: a compressed RANGE (height capped
at `max_range_atr_mult`x a long-term ATR baseline) must exist first --
"markup and markdown are only ever entered by leaving one" -- then an exit
from that range on WIDENING SPREAD (bar range >= `widening_spread_threshold`
x recent average) AND EXPANDING VOLUME (volume >=
`expanding_volume_threshold`x recent average) prints a Sign-of-Strength
(SOS) breakout; the markup phase only fully CONFIRMS once the first
pullback ("the back-up") holds beyond the old range boundary (doesn't
fall back inside) -- source's own words: "the phase confirms once the
first reaction holds beyond the old boundary."

This maps directly onto a long-only entry: a range-compression, breakout-
with-expansion, and first-pullback-holds sequence is exactly a disciplined
trend-following entry with a real structural confirmation step (distinct
from a naive single-bar breakout, which fires on the SOS bar alone without
waiting for the pullback test).

First "Markup & Markdown" strategy in this repo (0 prior hits for this
exact two-stage compression -> SOS-breakout -> pullback-confirmation
sequence; distinct from this repo's other range-breakout strategies which
either skip the pullback-confirmation step entirely or use different
range-detection logic, e.g. Trading-range Position tested earlier this
same cron trigger which trades WITHIN the range rather than its breakout).

Signal logic
------------
- Range detection: compressed when rolling (high.max - low.min) over
  `range_length` bars <= `max_range_atr_mult` * ATR(`atr_baseline_window`).
- SOS breakout: close breaks above the range's high AND today's bar range
  (high-low) >= `widening_spread_threshold` * rolling average range
  (`expansion_baseline_window`) AND volume >= `expanding_volume_threshold`
  * rolling average volume (same window).
- Pullback confirmation: within `reaction_pivot_length` * 3 bars after the
  SOS breakout, price pulls back but the low of that pullback stays ABOVE
  the old range's high (the "old boundary" -- doesn't fall back inside).
  If it does fall back inside, the setup is invalidated (no entry).
- Entry (long): at the confirmation bar's close (the bar where the
  pullback low is confirmed to have held, i.e. the first bar after the
  pullback's local low that closes higher again).
- Exit: close falls back below the (now-support) old range boundary
  (phase-ending per source's own "range resolving against the trend"
  rule), or a max_hold_days time-stop.

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


def _compute_trades(
    df: pd.DataFrame,
    range_length: int,
    max_range_atr_mult: float,
    atr_baseline_window: int,
    expansion_baseline_window: int,
    widening_spread_threshold: float,
    expanding_volume_threshold: float,
    reaction_pivot_length: int,
    max_hold_days: int,
):
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)

    range_high = high.rolling(range_length).max().shift(1)
    range_low = low.rolling(range_length).min().shift(1)
    atr = _atr(df, atr_baseline_window)
    compressed = (range_high - range_low) <= max_range_atr_mult * atr

    bar_range = high - low
    avg_range = bar_range.rolling(expansion_baseline_window).mean()
    avg_volume = volume.rolling(expansion_baseline_window).mean()

    sos_breakout = (
        (close > range_high)
        & (bar_range >= widening_spread_threshold * avg_range)
        & (volume >= expanding_volume_threshold * avg_volume)
        & compressed
    )

    n = len(df)
    close_arr = close.to_numpy()
    low_arr = low.to_numpy()
    high_arr = high.to_numpy()
    range_high_arr = range_high.to_numpy()
    sos_arr = sos_breakout.to_numpy()

    pullback_window = reaction_pivot_length * 3

    trades = []
    i = 0
    while i < n:
        if sos_arr[i]:
            boundary = range_high_arr[i]
            sos_idx = i
            # Watch the pullback window for a low that stays above the
            # boundary (confirmation) vs. falling back inside (invalidation).
            confirmed_idx = None
            invalidated = False
            local_low = close_arr[sos_idx]
            local_low_idx = sos_idx
            for k in range(sos_idx + 1, min(sos_idx + 1 + pullback_window, n)):
                if low_arr[k] < boundary:
                    invalidated = True
                    break
                if close_arr[k] < local_low:
                    local_low = close_arr[k]
                    local_low_idx = k
                elif k > local_low_idx and close_arr[k] > local_low and local_low_idx > sos_idx:
                    # First bounce after a local pullback low -> confirmation.
                    confirmed_idx = k
                    break
            if not invalidated and confirmed_idx is not None:
                entry_idx = confirmed_idx
                entry_price = close_arr[entry_idx]

                exit_idx = None
                for k in range(entry_idx + 1, min(entry_idx + 1 + max_hold_days, n)):
                    if close_arr[k] < boundary:
                        exit_idx = k
                        break
                if exit_idx is None:
                    exit_idx = min(entry_idx + max_hold_days, n - 1)
                exit_price = close_arr[exit_idx]

                trades.append((entry_idx, exit_idx, entry_price, exit_price))
                i = exit_idx + 1
                continue
        i += 1

    return trades


def generate_signals(
    price_df: pd.DataFrame,
    range_length: int = 20,
    max_range_atr_mult: float = 3.5,
    atr_baseline_window: int = 200,
    expansion_baseline_window: int = 20,
    widening_spread_threshold: float = 1.25,
    expanding_volume_threshold: float = 1.25,
    reaction_pivot_length: int = 3,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    trades = _compute_trades(
        df, range_length, max_range_atr_mult, atr_baseline_window,
        expansion_baseline_window, widening_spread_threshold,
        expanding_volume_threshold, reaction_pivot_length, max_hold_days,
    )
    pos = pd.Series(0.0, index=df.index)
    for entry_idx, exit_idx, _, _ in trades:
        pos.iloc[entry_idx : exit_idx + 1] = 1.0
    return pos


def generate_returns(
    price_df: pd.DataFrame,
    range_length: int = 20,
    max_range_atr_mult: float = 3.5,
    atr_baseline_window: int = 200,
    expansion_baseline_window: int = 20,
    widening_spread_threshold: float = 1.25,
    expanding_volume_threshold: float = 1.25,
    reaction_pivot_length: int = 3,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    trades = _compute_trades(
        df, range_length, max_range_atr_mult, atr_baseline_window,
        expansion_baseline_window, widening_spread_threshold,
        expanding_volume_threshold, reaction_pivot_length, max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = pd.Series(0.0, index=df.index)

    for entry_idx, exit_idx, entry_price, exit_price in trades:
        if exit_idx > entry_idx:
            strat_ret.iloc[entry_idx + 1 : exit_idx + 1] = daily_ret.iloc[
                entry_idx + 1 : exit_idx + 1
            ]
        exit_close = df["close"].iloc[exit_idx]
        if exit_close != 0 and exit_price != exit_close:
            prior_close = df["close"].iloc[exit_idx - 1] if exit_idx > 0 else df["close"].iloc[exit_idx]
            if prior_close != 0:
                strat_ret.iloc[exit_idx] = (exit_price / prior_close) - 1.0

    return strat_ret
