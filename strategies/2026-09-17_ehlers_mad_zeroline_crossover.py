"""Strategy: Ehlers MAD (Moving Average Difference) zero-line crossover.

Source: TASC (Technical Analysis of Stocks & Commodities) October 2021,
John F. Ehlers, "Cycle/Trend Analytics And The MAD Indicator", via the
TradingView Pine Script disclosed at
https://traders.com/documentation/feedbk_docs/2021/10/traderstips.html
(visited this iteration, see knowledge_base/visited_pages.jsonl):

    shortAvg = SMA(close, shortLength)   # default shortLength=8
    longAvg  = SMA(close, longLength)    # default longLength=23
    MAD = 100 * (shortAvg - longAvg) / longAvg

The source plots MAD green when > 0 and red when < 0 -- i.e. a
percent-normalized dual-SMA-difference trend indicator (similar spirit to
PPO/MACD-percent, but computed on two plain SMAs of price rather than EMAs
of MACD's own spread). First MAD entry in this repo (0 prior KB hits for
this exact construction) -- distinct from the already-tested MADH
(Hann-windowed variant, id=2026-09-12-162, rejected) which uses Hann-window
weighted SMAs and a different, un-normalized ratio-difference formula.

Trading rule (this repo's standard treatment for an undisclosed-precise-rule
zero-line trend indicator, consistent with prior PPO/DPO/MACD zero-cross
strategies in this repo): long when MAD crosses above zero (short SMA above
long SMA in percent terms, bullish trend), flat/exit when it crosses back
below zero, with a `min_hold_days` hysteresis gate to reduce whipsaw (same
pattern used successfully for several other Ehlers/oscillator crossovers in
this repo), plus an optional `max_hold_days` time-stop and an SMA
`trend_window` regime filter (only take longs when close is above its own
longer-term trend SMA, avoiding MAD crossovers during established
downtrends).

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


def _mad(close: pd.Series, short_length: int, long_length: int) -> pd.Series:
    short_avg = close.rolling(short_length).mean()
    long_avg = close.rolling(long_length).mean()
    return 100.0 * (short_avg - long_avg) / long_avg


def generate_signals(
    price_df: pd.DataFrame,
    short_length: int = 6,
    long_length: int = 18,
    trend_window: int = 100,
    min_hold_days: int = 5,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    mad = _mad(close, short_length, long_length)
    trend_sma = close.rolling(trend_window).mean()

    raw_long_signal = (mad > 0) & (close > trend_sma)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            want_flat = (not bool(raw_long_signal.iloc[i])) and held >= min_hold_days
            if want_flat or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(raw_long_signal.iloc[i]):
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
