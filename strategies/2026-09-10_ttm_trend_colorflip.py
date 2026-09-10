"""Strategy: TTM Trend (John Carter, "Mastering the Trade") bar-color
trend-following entry, with a color-flip exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-XXX):
Per tradegrub.com's "TTM Trend" indicator explainer (visited this
iteration, https://charts.tradegrub.com/indicators/ttm-trend) and
corroborated by thinkorswim's TTM_Trend documentation snippet ("a bar is
shown as bearish when the Average Price has closed in the lower 50% price
range of the input-defined number of previous bars"): the reference level
is the average of the midpoints ((high+low)/2) of the preceding
`lookback` bars (default 6). A bar is colored "up" when its close is
above that reference average, "down" when below. TTM Trend is explicitly
NOT a standalone standalone entry signal in its usual usage -- traders
hold through a colored run and exit on the first color flip (trailing
exit), per the source's own framing ("A run of same-coloured bars marks a
trend worth holding and the first colour change marks the trailing
exit").

This is a first TTM-Trend-specific strategy in this repo, distinct from
the already-tested-and-rejected TTM Squeeze / TTM Squeeze Pro (compression
+ momentum-histogram breakout strategies, id=2026-09-08-004,
2026-09-09-059) since TTM Trend uses no Bollinger/Keltner compression
concept at all -- it's a pure midpoint-average trend-color mechanism,
closer in spirit to Heikin-Ashi coloring but computed from real OHLC.

Signal logic
------------
- midpoint[t] = (high[t] + low[t]) / 2
- reference[t] = mean(midpoint[t-lookback : t])  (average of the prior
  `lookback` bars' midpoints, NOT including bar t itself)
- up_bar[t] = close[t] > reference[t]; down_bar[t] = close[t] < reference[t]
  (equal -> hold previous color, per source's tie-break rule)
- Entry (long): the color flips from down to up (first up bar after a
  down run), gated by a broader close > SMA(trend_window) filter to only
  take TTM-Trend up-flips in an already-established uptrend (this repo's
  own accumulated finding that a trend-regime filter improves most raw
  color/oscillator flips).
- Exit: color flips back to down, OR the trend filter breaks, OR a
  max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _ttm_trend_color(df: pd.DataFrame, lookback: int) -> pd.Series:
    """Return +1 (up bar), -1 (down bar), 0 (tie -> carries forward) per bar."""
    midpoint = (df["high"] + df["low"]) / 2.0
    reference = midpoint.rolling(lookback).mean().shift(1)  # prior `lookback` bars only
    close = df["close"]

    raw = pd.Series(np.nan, index=close.index)
    raw[close > reference] = 1
    raw[close < reference] = -1
    # Tie (close == reference) or NaN reference: carry forward previous color.
    color = raw.ffill()
    return color


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 6,
    trend_window: int = 100,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    color = _ttm_trend_color(df, lookback)
    prev_color = color.shift(1)
    up_flip = (prev_color == -1) & (color == 1)
    down_flip = (prev_color == 1) & (color == -1)

    sma = close.rolling(trend_window).mean()
    trend_up = close > sma

    entry = up_flip.fillna(False) & trend_up.fillna(False)
    exit_condition = down_flip.fillna(False) | (~trend_up.fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_condition.iloc[i]) or held >= max_hold_days:
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
