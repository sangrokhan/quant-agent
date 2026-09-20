"""Strategy: LBR 3/10 Oscillator (Linda Bradford Raschke) signal-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-XXX):
The "3/10 Oscillator" popularized by floor trader Linda Bradford Raschke is
an SMA-based MACD variant: fast_line = SMA(close, fast_window) -
SMA(close, slow_window); signal_line = SMA(fast_line, signal_window).
Per this iteration's research (Google SERP AI-overview + corroborating
forum/vendor pages, standard config fast=3/slow=10/signal=16): go long when
fast_line crosses above signal_line, flat when fast_line crosses below
signal_line. This is a distinct construction from every previously-tested
MACD/EMA-crossover variant in this repo (uses SMA not EMA, and a specific
3/10/16 parameterization never tested here) -- first LBR 3/10 Oscillator
entry in this KB (11 prior matches were all Raschke's OTHER indicators:
Turtle Soup, Momentum Pinball/LBR-RSI -- distinct techniques).

Signal logic
------------
- fast_line = SMA(close, fast_window) - SMA(close, slow_window)
- signal_line = SMA(fast_line, signal_window)
- Entry (long): fast_line crosses above signal_line (golden cross)
- Exit (flat): fast_line crosses below signal_line (dead cross)
- Always in market (long or flat), no separate stop/time-limit -- this
  is the oscillator's own native rule, tested as-is first before adding
  any regime filter in a follow-up iteration.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 3,
    slow_window: int = 10,
    signal_window: int = 16,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fast_sma = close.rolling(fast_window).mean()
    slow_sma = close.rolling(slow_window).mean()
    fast_line = fast_sma - slow_sma
    signal_line = fast_line.rolling(signal_window).mean()

    above = fast_line > signal_line
    prev_above = above.shift(1).fillna(False)

    golden_cross = above & (~prev_above)
    dead_cross = (~above) & prev_above

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if bool(golden_cross.iloc[i]):
            in_position = True
        elif bool(dead_cross.iloc[i]):
            in_position = False
        position.iloc[i] = 1 if in_position else 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias -- can't trade on today's own close).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
