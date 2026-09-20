"""Strategy: 52-Week High breakout entry, exit on 200-day SMA cross-below.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-116):
Per QuantifiedStrategies.com's "52-Week High Trading Strategy" article
(https://www.quantifiedstrategies.com/52-week-high-trading-strategy/),
citing academic work (Hong, Jordan & Liu, "Industry Information and the
52-Week High Effect") and a disclosed enlightenedstocktrading.com backtest:
stocks making a fresh 52-week (252 trading-day) closing high tend to
continue outperforming (an anchoring-bias / under-reaction effect -- market
participants use the 52-week high as a reference point and are slow to bid
prices past it, so momentum continues once it's cleared). The source's own
disclosed single-symbol-compatible rule set: enter long when today's close
is a new 252-day closing high; exit when the close crosses back below its
own 200-day SMA (disclosed as "Exit 1" in the source, CAGR 8.6%/MDD 44% on
their broad stock sample). First 52-week-high strategy in this repo (0
prior matches in strategies_index.jsonl for "52-week" or "52 week").

Signal logic
------------
- new_high_window-day (default 252, ~1 trading year) rolling max of close.
- Entry (long): close == the current new_high_window-day rolling max of
  close (i.e. today IS a new N-day closing high).
- Exit: close crosses below its own trend_sma_window-day SMA (default 200,
  per source's disclosed "Exit 1"), or a max_hold_days safety time-stop
  (not in source, added per this repo's standard practice to bound
  indefinite holds).
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


def generate_signals(
    price_df: pd.DataFrame,
    new_high_window: int = 252,
    trend_sma_window: int = 200,
    max_hold_days: int = 120,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rolling_high = close.rolling(new_high_window, min_periods=new_high_window).max()
    is_new_high = close >= rolling_high

    sma_trend = close.rolling(trend_sma_window).mean()
    below_sma = close < sma_trend

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_now = bool(below_sma.iloc[i]) or held >= max_hold_days
            if exit_now:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(is_new_high.iloc[i]):
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
