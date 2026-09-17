"""Strategy: Unger Weekly Factor Pattern breakout (daily-bar adaptation).

Source: TASC (Technical Analysis of Stocks & Commodities) September 2023
Traders' Tips (implementing the August 2023 article), Andrea Unger, "The
Weekly Factor Pattern", via
https://traders.com/Documentation/FEEDbk_docs/2023/09/TradersTips.html
(visited this iteration, see knowledge_base/visited_pages.jsonl), fully
disclosed TradeStation EasyLanguage:

    SessionListHigh = max(High) over the last 5 sessions
    SessionListLow  = min(Low) over the last 5 sessions
    WeeklyFactor = |Open[5 sessions ago] - Close[1 session ago]|
                   < RangeFilter * (SessionListHigh - SessionListLow)
    if WeeklyFactor: buy next bar at prior session's high, stop order
                     (source also sells short at prior session's low --
                     dropped here, long-only per SAFETY.md)

The source's original construction operates on INTRADAY session data
(CurrentSession/HighSession/LowSession functions -- designed for futures
trading multiple sessions per day). This repo's data/loaders.py only
provides daily OHLCV, so "session" here maps 1:1 to "daily bar": the
WeeklyFactor filter becomes a 5-DAY compression check (is the net
5-day open-to-close displacement small relative to the 5-day high-low
range?), and the breakout entry becomes "close breaks above yesterday's
high" rather than an intraday stop order. This compression proxy (open-N-
days-ago vs close-yesterday displacement, normalized by the same window's
high-low range) is a DISTINCT mechanism from every other squeeze/
compression strategy already tested in this repo (NR7 uses narrowest-bar-
range, Bollinger/Keltner squeezes use band-width percentile) -- first
Weekly Factor Pattern strategy in this repo.

Interface contract (see validation/grid_test.py, validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 5,
    range_filter: float = 0.5,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    open_ = df["open"]
    close = df["close"]

    session_high = high.rolling(window).max()
    session_low = low.rolling(window).min()
    session_range = session_high - session_low

    weekly_factor = (open_.shift(window - 1) - close.shift(1)).abs() < (
        range_filter * session_range
    )

    breakout_up = close > high.shift(1)
    entry_signal = weekly_factor & breakout_up

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    prior_low = low.shift(1)
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            failed = close.iloc[i] < prior_low.iloc[entry_idx] if entry_idx < len(prior_low) else False
            if held >= max_hold_days or bool(failed):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
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
