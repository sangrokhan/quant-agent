"""Strategy: Bear Power Zero-Cross Entry with Chandelier Trailing Stop Exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Per a Medium article by Kryptera, "The Regime Report: How to Find the
Strategy Inside Your Strategy" (summarized via Google AI-overview after
the direct article URL could not be resolved through search-result
click-through this iteration -- web_search DDGS backend TLS/connection-
reset errors throughout): the article's headline example strategy uses a
"Bears Power entry and Chandelier Trailing Stop exit" on Micron Technology
(MU), reporting a 42-year backtest with 76 trades and an eye-catching
cumulative return (110,256%) that the AI-overview summary itself flags as
likely overfit to a single ticker/period without walk-forward validation
-- exactly the caution this repo's own grid-test + walk-forward validator
suite is designed to catch.

This repo has 5+ prior Elder-Ray Bull/Bear Power entries (all using Bear
Power's own zero-line/slope dynamics for the ENTRY condition, paired with
EMA-slope filters, time-stops, or divergence patterns for the exit) and
1 prior Chandelier Exit strategy (2026-09-09-090, paired with SuperTrend
as a dual AND-gate, not with Bear Power). This entry is the first in this
repo to combine Bear Power (entry) with a genuine ATR-based Chandelier
Trailing Stop (exit) -- distinct from every prior Bear-Power exit
mechanism (EMA-slope reversal, divergence, mirrored bull/bear condition)
and every prior Chandelier Exit entry pairing (SuperTrend AND-gate,
EMA(50) breakout).

Signal logic
------------
- Bear Power = Low - EMA(ema_window). Bull Power = High - EMA(ema_window).
- Entry (long): Bear Power crosses from negative to less-negative (rising)
  while still below zero, AND the EMA itself is rising (uptrend proxy,
  per Elder's own recommendation used in this repo's prior Bear-Power
  entries) -- "bears losing conviction within an uptrend".
- Exit: price closes below the Chandelier long-stop line (highest high
  over chandelier_window periods, minus atr_mult * ATR(chandelier_window)),
  a classic volatility-adaptive trailing stop that only ever tightens
  (ratchets) in the favorable direction while in a position.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    ema_window: int = 13,
    chandelier_window: int = 22,
    atr_mult: float = 3.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    ema = close.ewm(span=ema_window, adjust=False).mean()
    bear_power = low - ema
    ema_rising = ema > ema.shift(1)

    bear_power_rising = bear_power > bear_power.shift(1)
    bear_power_negative = bear_power < 0
    entry_trigger = (bear_power_rising & bear_power_negative & ema_rising).shift(1).fillna(False)

    atr = _atr(df, chandelier_window)
    highest_high = high.rolling(chandelier_window).max()
    chandelier_long_stop = highest_high - atr_mult * atr

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    running_stop = None
    for i in range(len(close)):
        px = close.iloc[i]
        cs = chandelier_long_stop.iloc[i]
        if in_position:
            # Ratchet the stop up only (never loosen it).
            if running_stop is None or (cs == cs and cs > running_stop):
                running_stop = cs
            if running_stop is not None and px < running_stop:
                in_position = False
                running_stop = None
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
                in_position = True
                running_stop = cs if cs == cs else None
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
