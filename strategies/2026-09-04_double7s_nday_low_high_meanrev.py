"""Strategy: Larry Connors' "Double 7s" mean-reversion (N-day low entry / N-day high exit).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-114):
In a long-term uptrend, a short-term pullback to a fresh N-day low (default
N=7, the "Double 7" name comes from using 7 for both the entry and exit
lookback) marks a tactical dip-buying opportunity; the position is closed
when price recovers to a fresh N-day high, capturing the mean-reversion
bounce without needing to predict its exact magnitude.

Rules (per https://www.quantifiedstrategies.com/buy-the-dip-strategy/,
describing the original Larry Connors Double 7 rule which this repo's
"buy the dip" variant is explicitly derived from):
    1. close > SMA(trend_window) (200-day trend filter -- only buy dips
       within an established uptrend).
    2. close == rolling entry_window-day low of close (a fresh N-day low).
    3. If 1 and 2 are both true, go long at the close.
    4. Exit at the close when close == rolling exit_window-day high of
       close (a fresh N-day high) -- the original "Double 7" uses the same
       N for both entry and exit lookback (hence "double"); this repo also
       grid-tests asymmetric entry/exit windows. A max_hold_days safety
       time-stop is added since the source's own worked variants
       (7-day-low entry, 5-day-high OR next-up-close exit) show the exit
       condition sometimes takes a while to fire.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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
    trend_window: int = 200,
    entry_window: int = 7,
    exit_window: int = 7,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    rolling_low = close.rolling(entry_window).min()
    rolling_high = close.rolling(exit_window).max()

    fresh_low = close <= rolling_low
    fresh_high = close >= rolling_high

    entry = uptrend & fresh_low
    exit_signal = fresh_high

    valid = sma_trend.notna() & rolling_low.notna() & rolling_high.notna()

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(len(df)):
        if not valid.iloc[i]:
            position.iloc[i] = 0
            continue
        if in_pos:
            hold_count += 1
            if exit_signal.iloc[i] or hold_count >= max_hold_days:
                in_pos = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry.iloc[i]:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    entry_window: int = 7,
    exit_window: int = 7,
    max_hold_days: int = 15,
) -> pd.Series:
    """Daily strategy returns: yesterday's position times today's close-close return."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        trend_window=trend_window,
        entry_window=entry_window,
        exit_window=exit_window,
        max_hold_days=max_hold_days,
    )
    price_returns = df["close"].pct_change()
    strat_returns = position.shift(1).fillna(0) * price_returns
    return strat_returns.fillna(0.0)
