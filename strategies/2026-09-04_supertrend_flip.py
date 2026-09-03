"""Strategy: Supertrend (ATR-band stop-and-reverse flip), long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-053):
Per NetPicks' Supertrend guide: the Supertrend indicator overlays ATR-based
bands around the HL2 midpoint and flips direction when price closes on the
opposite side of the current band -- a distinct construction from every
prior indicator in this repo (combines ATR volatility bands with a
stop-and-reverse flip mechanic, similar in spirit to Parabolic SAR -042 but
using fixed-multiplier ATR bands around HL2 rather than an accelerating
extreme-point tracker). Standard params: ATR period=10, multiplier=3.

Supertrend formula (standard, Olivier Seban):
    HL2 = (high + low) / 2
    basic_upper = HL2 + multiplier * ATR(period)
    basic_lower = HL2 - multiplier * ATR(period)
    final_upper_t = basic_upper_t if (basic_upper_t < final_upper_{t-1} or close_{t-1} > final_upper_{t-1}) else final_upper_{t-1}
    final_lower_t = basic_lower_t if (basic_lower_t > final_lower_{t-1} or close_{t-1} < final_lower_{t-1}) else final_lower_{t-1}
    Supertrend flips to lower-band (bullish/long) when close crosses above
    final_upper; flips to upper-band (bearish/flat) when close crosses
    below final_lower.

Long-only implementation per repo convention: long while in the bullish
(green/lower-band) regime, flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def _supertrend(df: pd.DataFrame, atr_period: int = 10, multiplier: float = 3.0) -> pd.Series:
    """Return a boolean series: True = bullish (in lower-band regime)."""
    high, low, close = df["high"], df["low"], df["close"]
    hl2 = (high + low) / 2.0
    atr = _atr(df, atr_period)
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr

    idx = df.index
    final_upper = pd.Series(index=idx, dtype=float)
    final_lower = pd.Series(index=idx, dtype=float)
    bullish = pd.Series(index=idx, dtype=bool)

    first_valid_pos = atr.first_valid_index()
    if first_valid_pos is None:
        return pd.Series(False, index=idx)
    start_pos = list(idx).index(first_valid_pos)

    final_upper.iloc[start_pos] = basic_upper.iloc[start_pos]
    final_lower.iloc[start_pos] = basic_lower.iloc[start_pos]
    bullish.iloc[start_pos] = close.iloc[start_pos] > final_upper.iloc[start_pos]

    for i in range(start_pos + 1, len(idx)):
        bu = basic_upper.iloc[i]
        bl = basic_lower.iloc[i]
        prev_fu = final_upper.iloc[i - 1]
        prev_fl = final_lower.iloc[i - 1]
        prev_close = close.iloc[i - 1]

        fu = bu if (bu < prev_fu or prev_close > prev_fu) else prev_fu
        fl = bl if (bl > prev_fl or prev_close < prev_fl) else prev_fl
        final_upper.iloc[i] = fu
        final_lower.iloc[i] = fl

        prev_bull = bullish.iloc[i - 1]
        cur_close = close.iloc[i]
        if prev_bull:
            bullish.iloc[i] = cur_close > fl
        else:
            bullish.iloc[i] = cur_close > fu

    return bullish.fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    atr_period: int = 10,
    multiplier: float = 3.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    bullish = _supertrend(df, atr_period=atr_period, multiplier=multiplier)
    return bullish.astype(int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
