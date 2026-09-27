"""Strategy: Trading-range Position lower-third bounce (long-only).

Hypothesis (source: https://www.luxalgo.com/library/indicator/trading-range-position/,
read 2026-09-28 via browser_exec while browsing LuxAlgo's indicator library
for a fresh angle -- Pretty Good Oscillator/Polarized Fractal Efficiency/
Belt Hold all already saturated per strategies_index.jsonl novelty checks
this iteration):

LuxAlgo's "Trading-range Position" indicator formalizes a Wyckoff-style
range-trading idea: once a COMPRESSED window (default 20 bars, height
capped at `max_range_atr_mult`x a 200-period ATR baseline) confirms a
trading range, the range is split into a grid (thirds by default) and
every close is classified by which subdivision it sits in. Source's own
disclosed trading interpretation: "Territory entries: alerts fire when
price enters the lower or upper subdivision, where structural stops are
smallest relative to the ride across the range" -- i.e. buy in the bottom
third (structural stop just below the range low is cheap relative to the
ride back to the range's upper half), and the middle third is explicitly
a "no-trade zone" (source: "Neither location nor information favors range
entries there").

This is long-only per repo convention: buy when price enters the lower
third of a confirmed compressed range; exit when price reaches the middle
subdivision (partial target, source's own boundary) or the upper
subdivision (full target), OR the range resolves (breaks convincingly
above/below its own extremes, source's own "breakout confirmation" concept
via 2 consecutive closes beyond an extreme), OR a max_hold_days time-stop.

First "Trading-range Position" strategy in this repo (0 prior hits for this
exact construction; distinct from this repo's existing "Zscore Range Box"
and "Percentile Channel" range strategies which use different range-
detection/subdivision logic, and from generic support/resistance bounce
strategies which don't require an explicit compression-confirmed range
first).

Signal logic
------------
- Range detection: over the trailing `formation_length` bars, compute
  range_high = rolling max(high), range_low = rolling min(low). The range
  is "confirmed"/compressed when (range_high - range_low) <=
  `max_range_atr_mult` * ATR(`atr_baseline_window`).
- Position-in-range: pct_pos = (close - range_low) / (range_high - range_low),
  clipped to [0, 1].
- Subdivision boundaries (thirds): lower third = pct_pos <= 1/3, middle =
  1/3 < pct_pos < 2/3, upper third = pct_pos >= 2/3.
- Entry (long): range is confirmed/compressed AND close enters the lower
  third (fresh cross: pct_pos <= 1/3 today, was > 1/3 yesterday).
- Exit: pct_pos reaches >= 2/3 (upper third reached, full target), OR
  close breaks decisively below range_low (2 consecutive closes below,
  source's own breakout-confirmation rule -- range resolved downward,
  cut losses), OR a max_hold_days time-stop.

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
    formation_length: int,
    max_range_atr_mult: float,
    atr_baseline_window: int,
    breakout_confirmation: int,
    max_hold_days: int,
):
    close = df["close"]
    range_high = df["high"].rolling(formation_length).max()
    range_low = df["low"].rolling(formation_length).min()
    atr = _atr(df, atr_baseline_window)

    range_confirmed = (range_high - range_low) <= max_range_atr_mult * atr
    denom = (range_high - range_low).replace(0, np.nan)
    pct_pos = ((close - range_low) / denom).clip(lower=0.0, upper=1.0)

    lower_third = pct_pos <= (1.0 / 3.0)
    upper_third = pct_pos >= (2.0 / 3.0)
    fresh_lower_entry = lower_third & (~lower_third.shift(1).fillna(False)) & range_confirmed

    below_range = close < range_low
    breakout_down_streak = below_range.rolling(breakout_confirmation).sum() >= breakout_confirmation

    n = len(df)
    close_arr = close.to_numpy()
    entry_sig = fresh_lower_entry.to_numpy()
    upper_arr = upper_third.to_numpy()
    breakdown_arr = breakout_down_streak.to_numpy()

    trades = []
    i = 0
    while i < n:
        if entry_sig[i]:
            entry_idx = i
            entry_price = close_arr[i]
            exit_idx = None
            for k in range(entry_idx + 1, min(entry_idx + 1 + max_hold_days, n)):
                if bool(upper_arr[k]) or bool(breakdown_arr[k]):
                    exit_idx = k
                    break
            if exit_idx is None:
                exit_idx = min(entry_idx + max_hold_days, n - 1)
            exit_price = close_arr[exit_idx]
            trades.append((entry_idx, exit_idx, entry_price, exit_price))
            i = exit_idx + 1
        else:
            i += 1

    return trades


def generate_signals(
    price_df: pd.DataFrame,
    formation_length: int = 20,
    max_range_atr_mult: float = 3.0,
    atr_baseline_window: int = 200,
    breakout_confirmation: int = 2,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    trades = _compute_trades(
        df, formation_length, max_range_atr_mult, atr_baseline_window,
        breakout_confirmation, max_hold_days,
    )
    pos = pd.Series(0.0, index=df.index)
    for entry_idx, exit_idx, _, _ in trades:
        pos.iloc[entry_idx : exit_idx + 1] = 1.0
    return pos


def generate_returns(
    price_df: pd.DataFrame,
    formation_length: int = 20,
    max_range_atr_mult: float = 3.0,
    atr_baseline_window: int = 200,
    breakout_confirmation: int = 2,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    pos = generate_signals(
        df,
        formation_length=formation_length,
        max_range_atr_mult=max_range_atr_mult,
        atr_baseline_window=atr_baseline_window,
        breakout_confirmation=breakout_confirmation,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0.0)
    return strat_ret
