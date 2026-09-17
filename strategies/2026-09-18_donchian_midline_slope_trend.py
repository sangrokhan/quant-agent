"""Strategy: Donchian Channel Middle-Line SLOPE trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-004):
Per TASC August 2023 Traders' Tips ("Using Price Channels", Stella Osoba,
https://traders.com/Documentation/FEEDbk_docs/2023/08/TradersTips.html):
Donchian channel middle line = (Highest(High,N) + Lowest(Low,N)) / 2. The
MetaQuotes/MQL5 implementation shown for this same article explicitly
extends the plain channel with "the change in slope of the middle line to
determine the direction of the trend" -- a color-changing middle line
(green when rising, red when falling) with buy/sell arrows fired on the
slope flip itself. This is a genuinely distinct construction from every
Donchian-midline strategy already tested in this repo (all of which used
the midline as a PULLBACK/MEAN-REVERSION reference level: false-break-fade
2026-09-08-017, Rogue Kestrel CCI dual-confirmation 2026-09-10-069, general
midline-touch pullback rechecks) -- this iteration instead trades the
midline's own SLOPE DIRECTION as a standalone trend-following signal: long
entry when the middle line's own slope flips from falling/flat to rising
(midline_slope crosses above zero), exit when it flips back to
falling/flat (crosses back to <=0), gated by an SMA(trend_window) filter
to avoid trading Donchian-slope noise against the larger trend.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position series).
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
    channel_window: int = 20,
    slope_lookback: int = 3,
    trend_window: int = 100,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    upper = high.rolling(channel_window).max()
    lower = low.rolling(channel_window).min()
    middle = (upper + lower) / 2.0

    midline_slope = middle - middle.shift(slope_lookback)
    slope_rising = midline_slope > 0
    slope_flip_up = slope_rising & (~slope_rising.shift(1).fillna(False))
    slope_flip_down = (~slope_rising) & (slope_rising.shift(1).fillna(False))

    trend_up = close > close.rolling(trend_window).mean()

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(slope_flip_down.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(slope_flip_up.iloc[i]) and bool(trend_up.iloc[i]):
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
