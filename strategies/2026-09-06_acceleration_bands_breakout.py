"""Strategy: Acceleration Bands (Price Headley) two-consecutive-close breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-175):
Acceleration Bands are a momentum/breakout-oriented volatility band (opposite
orientation of most band systems, which fade extremes -- this one joins
strength). Per LuxAlgo's Acceleration Bands library page (first source to
disclose the exact mechanical rule for free; quantifiedstrategies.com's own
numeric rule set is paywalled, only the QQQ backtest summary stats are free):
  Upper = SMA(High * (1 + 4*(High-Low)/(High+Low)), N)
  Lower = SMA(Low  * (1 - 4*(High-Low)/(High+Low)), N)
  Midline = SMA(Close, N)
  Bullish breakout entry = TWO CONSECUTIVE closes above the Upper Band (the
    "classic acceleration entry" -- source explicitly requires 2 closes, not
    1, to filter single-bar noise breaches).
  Breakout exit = the FIRST close back inside the broken band (i.e. close
    drops back below Upper Band after being in an acceleration phase).
This repo adds a max_hold_days time-stop backstop (source gives no explicit
max hold) and an optional trend_window SMA gate (only take breakouts when
close is above a longer trend SMA, avoiding false breakouts in downtrends --
a standard adaptation used elsewhere in this repo for breakout strategies,
e.g. Donchian/Keltner/Bollinger-squeeze variants) as a tunable parameter to
grid-test against the ungated version.

First Acceleration Bands strategy tested in this repo (STARC Bands, tested
twice -- 2026-09-04-146/2026-09-06-141, both rejected -- use a *mean
reversion* rule off an ATR-based band; Acceleration Bands are a fundamentally
different momentum/breakout orientation off a high/low-range-derived band,
not ATR, and require two consecutive confirming closes rather than a single
touch).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _acceleration_bands(df: pd.DataFrame, window: int = 20, band_factor: float = 4.0):
    high = df["high"]
    low = df["low"]
    close = df["close"]
    range_frac = band_factor * (high - low) / (high + low).replace(0, pd.NA)
    upper_raw = high * (1 + range_frac)
    lower_raw = low * (1 - range_frac)
    upper = upper_raw.rolling(window).mean()
    lower = lower_raw.rolling(window).mean()
    midline = close.rolling(window).mean()
    return upper, lower, midline


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 20,
    band_factor: float = 4.0,
    trend_window: int = 0,  # 0 = no trend filter; otherwise require close > SMA(trend_window)
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    upper, lower, _midline = _acceleration_bands(df, window=window, band_factor=band_factor)

    above_upper = close > upper
    two_closes_above = above_upper & above_upper.shift(1).fillna(False)

    trend_ok = pd.Series(True, index=close.index)
    if trend_window and trend_window > 0:
        trend_sma = close.rolling(trend_window).mean()
        trend_ok = close > trend_sma

    entry = two_closes_above & trend_ok.fillna(False)
    exit_back_inside = close < upper  # first close back inside the broken upper band

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_back_inside.iloc[i]) or held >= max_hold_days:
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
