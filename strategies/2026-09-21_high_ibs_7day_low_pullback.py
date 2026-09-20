"""Strategy: high-IBS 7-day-low pullback (QuantifiedStrategies "4th Free
Strategy", QQQ pullback).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-177):
Per quantifiedstrategies.com's "4th Free Strategy!" article
(https://www.quantifiedstrategies.com/4th-free-strategy/), a fully-disclosed
QQQ pullback strategy with exact AmiBroker code:

    Buy = ref(IBS,-1) > 0.5 AND Ref(L,-1) < Ref(LLV(L,7),-2) AND C < Ref(C,-1)
    Sell = C > Ref(H,-1)

In plain English: yesterday's IBS (Internal Bar Strength = (close-low)/
(high-low)) was >= 0.5 (yesterday closed in the upper half of its own
range -- a relatively strong bar), AND yesterday's low broke below the
lowest low of the 7 days before that (a fresh short-term breakdown), AND
today's close is lower than yesterday's close (continuing weakness today).
Exit when today's close breaks back above yesterday's high.

This is distinct from every other IBS entry already in this repo, which all
use LOW IBS (oversold panic, near the day's low) as the entry trigger --
here IBS >= 0.5 (a relatively strong close) is combined with a fresh 7-day
breakdown and a down-day filter, i.e. buying strength-within-weakness during
an emerging pullback, not a pure oversold panic signal. Source's own
backtest (QQQ, commissions/slippage 0.03%/trade included): 179 trades, 77%
win rate, profit factor 3.5, CAGR 8.5% at only 8% market exposure (100%
risk-adjusted return), max drawdown 17% (buy-and-hold 82%).

Signal logic
------------
- IBS = (close - low) / (high - low), with the high==low degenerate case
  mapped to IBS=0.5 (undefined range).
- N-day low of `low`, computed BEFORE the immediately preceding day (i.e.
  the 7 days prior to yesterday, matching the source's `Ref(LLV(L,7),-2)`).
- Entry (long, at today's close): yesterday's IBS >= ibs_threshold (0.5)
  AND yesterday's low < that prior-7-day low AND today's close < yesterday's
  close.
- Exit (at today's close): today's close > yesterday's high.
- Flat otherwise (no position).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series
        {0,1} position series aligned to price_df.index.
    generate_returns(price_df, **params) -> pd.Series
        Position-weighted daily returns (position shifted by 1 day to avoid
        look-ahead bias), no transaction costs applied here.
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
    ibs_threshold: float = 0.4,
    lookback_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    rng = (high - low).replace(0.0, float("nan"))
    ibs = ((close - low) / rng).fillna(0.5)

    # Ref(LLV(L,7),-2): the 7-day low of `low` computed over the window
    # ENDING 2 bars ago (i.e. excluding yesterday and today).
    llv7 = low.rolling(lookback_days).min()
    llv7_lagged = llv7.shift(2)

    ibs_yday = ibs.shift(1)
    low_yday = low.shift(1)
    close_yday = close.shift(1)
    high_yday = high.shift(1)

    entry = (
        (ibs_yday >= ibs_threshold)
        & (low_yday < llv7_lagged)
        & (close < close_yday)
    )
    exit_signal = close > high_yday

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]) if not pd.isna(entry.iloc[i]) else False:
                in_position = True
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
