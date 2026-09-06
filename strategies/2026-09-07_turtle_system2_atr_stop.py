"""Strategy: Turtle Trading System 2 (55-day breakout, always taken, 20-day
opposite-extreme exit, 2N ATR stop).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-014):
Per https://www.theturtletrader.com/turtle-trading-rules: System 2 is the
Turtles' longer-term companion system to System 1 (already tested in this
repo, id=2026-09-06-125, accepted). Entry: buy at close on a new 55-day
high. Unlike System 1, EVERY System 2 signal is taken -- no "skip after a
winning breakout" filter (the source: "Every signal is taken, no filter").
Exit: close makes a new 20-day low (System 2's own opposite-extreme exit,
vs System 1's 10-day exit), or the 2N ATR protective stop, whichever comes
first. N = 20-day average true range, identical construction to System 1.
This is a genuinely distinct strategy from System 1: longer entry/exit
windows (55/20 vs 20/10) intended to catch the rarer, longer trends that
System 1's tighter windows would exit prematurely, and no skip-after-win
signal filtering at all.

Signal logic (long-only, per SAFETY.md -- no short leg)
------------
- N = 20-day rolling mean of True Range (Wilder-style, same as System 1).
- Entry (long): close makes a new `entry_window`-day high (default 55).
  Every signal taken (no skip filter).
- Exit: close makes a new `exit_window`-day low (default 20) OR close drops
  to/below (entry_price - stop_atr_mult * N at entry) (2N protective stop),
  whichever triggers first, OR a `max_hold_days` time-stop (extra robustness
  cap not in the original, to avoid indefinite holds).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def generate_signals(
    price_df: pd.DataFrame,
    entry_window: int = 55,
    exit_window: int = 20,
    atr_window: int = 20,
    stop_atr_mult: float = 2.0,
    max_hold_days: int = 90,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    n_atr = _true_range(df).rolling(atr_window).mean()

    entry_high = high.rolling(entry_window).max().shift(1)
    exit_low = low.rolling(exit_window).min().shift(1)

    entry_signal = close > entry_high

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = 0.0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            el = exit_low.iloc[i]
            hit_low_exit = bool(el is not None and not pd.isna(el) and close.iloc[i] < el)
            hit_stop = close.iloc[i] <= stop_price
            hit_time = held >= max_hold_days
            if hit_low_exit or hit_stop or hit_time:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            can_enter = bool(entry_signal.iloc[i])
            if can_enter and not pd.isna(n_atr.iloc[i]) and n_atr.iloc[i] > 0:
                in_position = True
                entry_idx = i
                entry_price = close.iloc[i]
                stop_price = entry_price - stop_atr_mult * n_atr.iloc[i]
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
