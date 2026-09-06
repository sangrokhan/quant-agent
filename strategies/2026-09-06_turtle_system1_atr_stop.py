"""Strategy: Turtle Trading System 1 (20-day breakout) with 2N ATR stop-loss
and the classic "skip after a win" filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-125):
The original 1983 Turtle Trading System 1 rule: enter long at the close on a
new 20-day high; place an initial protective stop at entry - 2N, where N is
the 20-day (Wilder-style) Average True Range; exit on whichever comes first
of the 2N stop-loss or a new 10-day low (System 1's own exit rule). The
System-1-specific "skip rule" (per the Google AI-overview summary read this
iteration, sourced from JournalPlus/TrendSpider/Trading Dude Turtle-rule
write-ups): skip the next 20-day breakout entry signal if the most recently
closed System-1 trade in this same instrument was a winner -- the original
turtles' rationale being that System 1 breakouts cluster and a recent
winning breakout has "used up" the edge for the next correlated one, so
System 2 (55-day, always taken) picks up the bigger trend moves instead.
This repo already tested a *plain* Donchian 20-high/10-low breakout
(2026-09-04-054, accepted on QQQ only) without either the ATR-based
stop-loss or the skip-after-win filter -- this strategy is a genuinely
different construction because it adds (a) a volatility-sized protective
stop that can exit a trade before the 10-day-low signal fires, and (b) the
skip-after-win filter that mechanically avoids some breakout entries
entirely, both absent from -054.

Source: Google AI-overview summary of the Turtle Trading System rules
(read via browser_exec at
https://www.google.com/search?q=Turtle+Trading+System+rules+20-day+55-day+breakout+entry+exit+N+ATR
after web_search returned "No results found"), citing JournalPlus,
TrendSpider, Trading Dude, and Ultima Markets as its source snippets.

Signal logic
------------
- N = 20-day rolling mean of True Range (max(high-low, |high-prev_close|,
  |low-prev_close|)) -- the Turtles' definition of "N".
- Entry (long): close makes a new `entry_window`-day high (default 20,
  System 1) AND the most recently closed trade (if any) in this series was
  NOT a winner (skip-after-win rule). The very first breakout ever seen is
  always taken (no prior trade to check).
- Exit: close makes a new `exit_window`-day low (default 10, System 1's own
  exit) OR close drops to/below (entry_price - stop_atr_mult * N at entry)
  (2N protective stop, default stop_atr_mult=2.0), whichever triggers
  first, OR a `max_hold_days` time-stop as an extra robustness cap not in
  the original (avoids indefinite holds when neither exit condition fires
  for a very long trending stretch).
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
    entry_window: int = 20,
    exit_window: int = 10,
    atr_window: int = 20,
    stop_atr_mult: float = 2.0,
    max_hold_days: int = 60,
    skip_after_win: bool = True,
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
    entry_price = 0.0
    stop_price = 0.0
    last_trade_won = None  # None = no prior trade yet

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            hit_low_exit = bool(exit_low.iloc[i] is not None and not pd.isna(exit_low.iloc[i]) and close.iloc[i] < exit_low.iloc[i])
            hit_stop = close.iloc[i] <= stop_price
            hit_time = held >= max_hold_days
            if hit_low_exit or hit_stop or hit_time:
                in_position = False
                last_trade_won = close.iloc[i] > entry_price
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            can_enter = bool(entry_signal.iloc[i])
            if skip_after_win and can_enter and last_trade_won is True:
                # Skip this breakout signal (System 1 skip-after-win rule);
                # reset so the *next* fresh breakout is evaluated normally.
                can_enter = False
                last_trade_won = None
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
