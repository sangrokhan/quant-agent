"""Strategy: TEMA pullback re-entry within a confirmed uptrend.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-056):
Per arrowalgo.com's TEMA (Triple Exponential Moving Average, Patrick Mulloy)
guide "pullback re-entry" strategy: during a confirmed uptrend (price above
a slow 50-period TEMA), wait for a pullback where price touches/dips to the
faster 20-period TEMA, then enter long on the next bullish candle (close >
open). This captures swing entries within a larger trend rather than
chasing breakouts. First TEMA-based construction in this repo (existing
hits are Hull/T3/other adaptive-MA families, not TEMA specifically).

Signal logic
------------
- TEMA(n) = 3*EMA1 - 3*EMA2 + EMA3, where EMA1=EMA(close,n),
  EMA2=EMA(EMA1,n), EMA3=EMA(EMA2,n) (standard triple-smoothed construction).
- Uptrend confirmed: close > TEMA(slow_period).
- Pullback: close <= TEMA(fast_period) * (1 + pullback_tolerance) (price at
  or below the fast TEMA, within a small tolerance band).
- Entry (long): uptrend confirmed AND pullback condition AND the current
  bar is bullish (close > open) -- the "next bullish candle" confirmation.
- Exit: close falls below TEMA(slow_period) (trend break), OR after
  max_hold_days trading days.
- Flat (no position) whenever not in an active long.

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


def _tema(close: pd.Series, n: int) -> pd.Series:
    ema1 = close.ewm(span=n, adjust=False).mean()
    ema2 = ema1.ewm(span=n, adjust=False).mean()
    ema3 = ema2.ewm(span=n, adjust=False).mean()
    return 3 * ema1 - 3 * ema2 + ema3


def generate_signals(
    price_df: pd.DataFrame,
    fast_period: int = 20,
    slow_period: int = 50,
    pullback_tolerance: float = 0.01,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]

    tema_fast = _tema(close, fast_period)
    tema_slow = _tema(close, slow_period)

    uptrend = close > tema_slow
    pullback = close <= tema_fast * (1 + pullback_tolerance)
    bullish_candle = close > open_

    entry = uptrend & pullback & bullish_candle
    exit_trend_break = close < tema_slow

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
