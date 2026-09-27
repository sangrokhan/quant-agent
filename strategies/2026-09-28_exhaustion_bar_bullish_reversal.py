"""Strategy: Bullish Exhaustion Bar reversal (long-only).

Hypothesis (source: https://www.luxalgo.com/library/indicator/exhaustion-bar/,
read 2026-09-28 via browser_exec while browsing LuxAlgo's indicator library
for a fresh angle -- Gann HiLo/Double Bollinger Zones/Jump Detection/RSI
Failure Swing all already saturated or previously tried per
strategies_index.jsonl novelty checks this iteration):

LuxAlgo's "Exhaustion Bar" indicator codifies a "maximum-effort,
minimal-result" candle: ALL of the following must hold simultaneously --
(1) an extended prior directional move of >= `min_prior_move_atr_mult` x
ATR over `trend_lookback` bars, (2) a fresh extreme (new low, for the
bullish/downtrend-exhaustion case) of that lookback, (3) a range well
beyond the recent average range (>= `wide_range_multiplier`x, optionally
with a volume spike), and (4) a close finishing near the BAR'S OPPOSITE
extreme (within `close_location_pct`% of the top, for a bearish-move
exhaustion), by default back inside the prior bars' range so the
downward excursion is left as a rejected wick. Source's own framing:
"the exhaustion bar is only hunted where there is something to exhaust"
-- i.e. it specifically requires a stretched prior move, not just any
wide-range reversal candle.

We trade the BULLISH case (downtrend exhaustion): after a stretched
decline making a fresh N-bar low, a wide-range bar that closes back up
near its own high (a rejected lower wick) signals sellers are exhausted
and a reversal bounce is likely. Long entry at that bar's close (or, with
`require_confirmation=True`, the next bar's close beyond the exhaustion
bar's midpoint, per source's own optional "later but substantially
cleaner" confirmation rule); stop below the exhaustion bar's own low
(source's own stated stop placement: "the natural stop sits beyond
[the wick tip]"); target = `reward_r_multiple` R; `max_hold_days`
time-stop.

First "Exhaustion Bar" strategy in this repo (0 prior hits for this exact
LuxAlgo construction -- distinct from the already-tested/rejected RVOL
Exhaustion-Climax Reversal [2026-09-27-004, decisive signal-starvation
rejection using a much simpler RVOL-only definition] and the No-Wick
Retest Levels strategy [different no-wick-not-wide-range construction]).

Signal logic
------------
- prior_move = |close[t-trend_lookback] to close[t] change| over the
  trailing trend_lookback bars, direction-agnostic per source's "0 =
  direction only" option; we require it specifically DOWNWARD (bearish
  prior move) for the bullish-reversal case: close[t-lookback] - close[t]
  >= min_prior_move_atr_mult * ATR(atr_window).
- fresh_extreme: today's low is the lowest low over the trailing
  trend_lookback bars (inclusive).
- wide_range: today's (high-low) >= wide_range_multiplier * rolling
  average range (effort_avg_window).
- close_location: (close - low) / (high - low) >= (1 - close_location_pct/100)
  (close near the bar's own high).
- close_back_inside: today's low < yesterday's low (the excursion made a
  new extreme) AND today's close > yesterday's low (closed back inside
  the prior bar's range -- the "rejected wick" requirement).
- Entry: all conditions hold -> long entry at this bar's close (or next
  bar's confirmation close if require_confirmation).
- Exit: stop below exhaustion bar's low, target = entry + reward_r_multiple
  * (entry - stop), or max_hold_days time-stop.

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


def _detect_exhaustion_bars(
    df: pd.DataFrame,
    trend_lookback: int,
    min_prior_move_atr_mult: float,
    atr_window: int,
    effort_avg_window: int,
    wide_range_multiplier: float,
    close_location_pct: float,
) -> pd.Series:
    close = df["close"]
    low = df["low"]
    high = df["high"]
    atr = _atr(df, atr_window)

    prior_move = close.shift(trend_lookback) - close
    stretched_decline = prior_move >= min_prior_move_atr_mult * atr

    fresh_low = low <= low.rolling(trend_lookback).min()

    bar_range = high - low
    avg_range = bar_range.rolling(effort_avg_window).mean()
    wide_range = bar_range >= wide_range_multiplier * avg_range

    denom = bar_range.replace(0, np.nan)
    close_loc = (close - low) / denom
    close_near_high = close_loc >= (1 - close_location_pct / 100.0)

    close_back_inside = (low < low.shift(1)) & (close > low.shift(1))

    return stretched_decline & fresh_low & wide_range & close_near_high & close_back_inside


def _compute_trades(
    df: pd.DataFrame,
    trend_lookback: int,
    min_prior_move_atr_mult: float,
    atr_window: int,
    effort_avg_window: int,
    wide_range_multiplier: float,
    close_location_pct: float,
    reward_r_multiple: float,
    max_hold_days: int,
):
    exhaustion = _detect_exhaustion_bars(
        df, trend_lookback, min_prior_move_atr_mult, atr_window,
        effort_avg_window, wide_range_multiplier, close_location_pct,
    ).to_numpy()

    close = df["close"].to_numpy()
    low = df["low"].to_numpy()
    high = df["high"].to_numpy()
    n = len(df)

    trades = []
    i = 0
    while i < n:
        if exhaustion[i]:
            entry_idx = i
            entry_price = close[i]
            stop_price = low[i]
            risk = entry_price - stop_price
            if risk <= 0:
                i += 1
                continue
            target_price = entry_price + reward_r_multiple * risk

            exit_idx = None
            exit_price = None
            for k in range(entry_idx + 1, min(entry_idx + 1 + max_hold_days, n)):
                if low[k] <= stop_price:
                    exit_idx = k
                    exit_price = stop_price
                    break
                if high[k] >= target_price:
                    exit_idx = k
                    exit_price = target_price
                    break
            if exit_idx is None:
                exit_idx = min(entry_idx + max_hold_days, n - 1)
                exit_price = close[exit_idx]

            trades.append((entry_idx, exit_idx, entry_price, exit_price))
            i = exit_idx + 1
        else:
            i += 1

    return trades


def generate_signals(
    price_df: pd.DataFrame,
    trend_lookback: int = 20,
    min_prior_move_atr_mult: float = 2.0,
    atr_window: int = 14,
    effort_avg_window: int = 20,
    wide_range_multiplier: float = 1.5,
    close_location_pct: float = 25.0,
    reward_r_multiple: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    trades = _compute_trades(
        df, trend_lookback, min_prior_move_atr_mult, atr_window,
        effort_avg_window, wide_range_multiplier, close_location_pct,
        reward_r_multiple, max_hold_days,
    )
    pos = pd.Series(0.0, index=df.index)
    for entry_idx, exit_idx, _, _ in trades:
        pos.iloc[entry_idx : exit_idx + 1] = 1.0
    return pos


def generate_returns(
    price_df: pd.DataFrame,
    trend_lookback: int = 20,
    min_prior_move_atr_mult: float = 2.0,
    atr_window: int = 14,
    effort_avg_window: int = 20,
    wide_range_multiplier: float = 1.5,
    close_location_pct: float = 25.0,
    reward_r_multiple: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    trades = _compute_trades(
        df, trend_lookback, min_prior_move_atr_mult, atr_window,
        effort_avg_window, wide_range_multiplier, close_location_pct,
        reward_r_multiple, max_hold_days,
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
