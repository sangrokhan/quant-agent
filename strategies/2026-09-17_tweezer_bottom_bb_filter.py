"""Strategy: Tweezer Bottom candlestick pattern + Bollinger Band oversold filter.

Source: https://www.quantifiedstrategies.com/tweezer-bottom-candlestick/
(visited this iteration via browser_exec -- web_search DDGS/Yahoo backend
down with RequestError/TLS errors on every query attempted this iteration).
First Tweezer Bottom entry in this repo (0 prior KB hits).

Pattern definition (source's own exact definition):
    "A tweezer bottom forms in a developed bearish trend and may consist of
    several candles... The first candle has a significant lower wick. It
    may be bullish or bearish. The second candle may also be bullish or
    bearish, and revisits the low of the previous candle, without breaking
    it." Operationalized here as exactly two consecutive candles: candle[i-1]
    has a low, and candle[i]'s low stays within `tolerance_pct` of
    candle[i-1]'s low (revisits without breaking it -- allowing a tiny
    tolerance for near-exact double-bottom low matches on real data, since
    an exact float match never occurs) AND candle[i]'s low is not lower
    than candle[i-1]'s low by more than the tolerance (the defended-low
    condition).

Trading rule (source's own disclosed "Trading Strategy 1: Tweezer Bottom
With Bollinger Band Filter", verbatim): "the rules to go long will be that:
There is a tweezer bottom. The close is below the lower Bollinger band...
Then we'll exit after 5 bars." Implemented here with configurable
`bb_window`/`bb_std` (defaults 20/2.0, standard Bollinger construction) and
configurable `exit_bars` (default 5, matching the source's stated fixed
exit).

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


def _is_tweezer_bottom(low: pd.Series, tolerance_pct: float) -> pd.Series:
    """True on bar i if low[i] revisits low[i-1] without breaking it
    (within tolerance_pct), the source's exact "defended low" condition."""
    prev_low = low.shift(1)
    diff_pct = (low - prev_low).abs() / prev_low
    not_broken = low >= prev_low * (1 - tolerance_pct)
    revisits = diff_pct <= tolerance_pct
    return not_broken & revisits


def generate_signals(
    price_df: pd.DataFrame,
    tolerance_pct: float = 0.003,
    bb_window: int = 20,
    bb_std: float = 2.0,
    exit_bars: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]

    tweezer = _is_tweezer_bottom(low, tolerance_pct)

    sma = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    lower_band = sma - bb_std * std
    oversold = close < lower_band

    raw_long_signal = tweezer & oversold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= exit_bars:
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
