"""Strategy: REX Oscillator trend-continuation pullback entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-059):
Per quantifiedstrategies.com's REX Oscillator article (disclosed formula,
numeric backtest rule paywalled): the REX Oscillator is a moving average of
the "True Value of a Bar" (TVB = 3*Close - (Low + Open + High), equivalently
(Close-Low) + (Close-Open) - (High-Close)), oscillating around zero. The
source's own described "trend-continuation strategy": in an established
uptrend, a countertrend pullback that reaches a key level, followed by REX
crossing from negative back to positive, signals the pullback is ending and
the uptrend is about to resume -- a long entry. This strategy operationalizes
that exact description: close > SMA(trend_window) defines the uptrend; REX
having been negative (below zero) within the recent lookback marks an active
pullback; REX crossing from <=0 to >0 is the entry trigger. Exit on REX
crossing back below zero (source's own stated primary use case for REX --
"typically seen as an exit signal"), the trend filter breaking, or a
max_hold_days time-stop. First REX Oscillator strategy in this repo --
distinct from the price-bar-wick-based Rob Hanna IBS family (uses only
Close/Low/High, no Open) and from Elder's Force Index / other bar-strength
oscillators already tested. Source:
https://www.quantifiedstrategies.com/rex-oscillator/

Signal logic
------------
- TVB = 3*Close - (Low + Open + High)
- REX = EMA(TVB, rex_period)
- Uptrend: close > SMA(trend_window)
- Pullback-active: REX was <= 0 at some point within pullback_lookback bars
- Entry (long): uptrend AND pullback-active AND REX crosses from <=0 to >0
  (bullish zero-line cross)
- Exit: REX crosses back below zero, OR trend filter breaks (close <=
  SMA(trend_window)), OR after max_hold_days trading days.
- Flat (no position) otherwise.

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


def generate_signals(
    price_df: pd.DataFrame,
    rex_period: int = 21,
    trend_window: int = 50,
    pullback_lookback: int = 10,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]

    tvb = 3 * close - (low + open_ + high)
    rex = tvb.ewm(span=rex_period, adjust=False).mean()

    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    was_negative = (rex <= 0).rolling(pullback_lookback).max().astype(bool).shift(1).fillna(False)
    rex_cross_up = (rex > 0) & (rex.shift(1) <= 0)
    entry = uptrend & was_negative & rex_cross_up

    exit_rex_cross_down = rex < 0
    exit_trend_break = ~uptrend

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_rex_cross_down.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
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
