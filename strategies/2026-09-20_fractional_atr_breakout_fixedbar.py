"""Strategy: Fractional-ATR-Distance Breakout, Fixed-Bar Exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-137):
Per Ali Casey's StatOasis article "Same Breakout Strategy, Different
Results: Nasdaq vs. SP500 vs. Dow"
(https://statoasis.com/overfit/research/same-breakout-strategy-different-results-nasdaq-vs-sp500-vs-dow,
visited via browser_exec this iteration): a deliberately minimal
long-only breakout system with a small fractional-ATR entry threshold
above the prior day's close (entry trigger = next bar's high clears
prior_close + atr_frac * ATR(atr_window), a small 0.25x multiple in the
source rather than the larger 1.5-3x multiples typical of Turtle/Chande-
Kroll-style breakout stops already tested in this repo) and a completely
mechanical fixed-bar exit (no trailing stop, no profit target, no signal-
based exit -- just hold for exactly hold_days bars). The source's own
comparison found this "Close + ATR distance" variant was the best-
performing of four tested breakout triggers on S&P 500 and Dow futures
specifically (a plain close>prior-close breakout won on Nasdaq instead).
This tests the source's own best-for-SPY/Dow variant on this repo's
equity/crypto universe. First fractional-ATR-distance-from-close breakout
with a fixed-bar-count exit in this repo (distinct from Chande Kroll Stop,
SuperTrend, and Turtle-style ATR breakouts, which all use larger ATR
multiples for the initial trigger AND a trailing-stop or signal-based
exit rather than a pure fixed-holding-period exit).

Signal logic
------------
- entry_level = prior day's close + atr_frac * ATR(atr_window).
- Entry (long): today's high clears entry_level (simulating a buy-stop
  order placed at that level the source's own rule implies -- "next bar
  at Previous Close + ATR(10) x 0.25").
- Exit: exactly hold_days bars after entry, unconditionally (the source's
  own stated mechanic -- "Exit: Fixed number of bars (5) after entry").
- No stop-loss, no profit target, no trend filter -- deliberately minimal,
  matching the source's own "no complicated oscillators... no stop loss"
  design philosophy.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    atr_window: int = 10,
    atr_frac: float = 0.25,
    hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    atr = _atr(df, atr_window)
    entry_level = close.shift(1) + atr_frac * atr.shift(1)
    entry_trigger = (high >= entry_level).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
                in_position = True
                entry_idx = i
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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
