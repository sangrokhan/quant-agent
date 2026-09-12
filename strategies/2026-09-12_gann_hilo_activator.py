"""Strategy: Gann Hi-Lo Activator (GHLA) standalone state-flip trend follow.

Hypothesis (see knowledge_base entry): per Robert Krausz's 1998 Stocks &
Commodities article, reproduced at
https://financial-hacker.com/petra-on-programming-the-gann-hi-lo-activator/
(fully disclosed C code): the Gann Hi-Lo Activator (GHLA) flips a
bull/bear state when price crosses the trailing SMA of highs (bearish->
bullish) or the trailing SMA of lows (bullish->bearish), carrying the
previous state forward while price sits between the two bands. The
source's own test combined GHLA with two other indicators (DMI, SMI) in a
triple-confirmation swing system and found a net-zero 2015-2020 result --
but explicitly suggested the standalone GHLA with different entry
conditions might work better. This repo tests standalone GHLA state-flip
trend-following, distinct from the source's own negative-result 3-way
combo.

Algorithm (fully disclosed by source):
    ma_high[t] = SMA(high, h_period)[t]
    ma_low[t]  = SMA(low, l_period)[t]
    if close[t] > ma_high[t-1]: state[t] = +1
    elif close[t] < ma_low[t-1]: state[t] = -1
    else: state[t] = state[t-1]   (carry forward)

Long-only adaptation: long while state == +1, flat while state == -1 (or
undefined at the start of the series).

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
    h_period: int = 10,
    l_period: int = 10,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    ma_high = high.rolling(h_period).mean().shift(1)
    ma_low = low.rolling(l_period).mean().shift(1)

    state = pd.Series(0, index=close.index, dtype=int)
    prev_state = 0
    for i in range(len(close)):
        c = close.iloc[i]
        mh = ma_high.iloc[i]
        ml = ma_low.iloc[i]
        if pd.notna(mh) and c > mh:
            prev_state = 1
        elif pd.notna(ml) and c < ml:
            prev_state = -1
        state.iloc[i] = prev_state

    position = (state == 1).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
