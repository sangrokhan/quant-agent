"""Strategy: Supertrend stop-and-reverse flip, gated by a Choppiness Index
trending-regime filter (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-075):
Per TrendsAndBreakouts' Choppiness Index guide
(https://trendsandbreakouts.com/choppiness-index, browser_exec fallback --
web_search DDGS errored with a connection error for the direct query), the
Choppiness Index (CHOP, Bill Dreiss, 0-100 non-directional regime
classifier) below ~38 signals a trending market suitable for
trend-following signals; above ~62 signals a choppy/ranging market where
trend-following systems whipsaw. The source's standard recommendation is
to gate ANY trend-following signal with a CHOP<threshold filter. This
repo already has CHOP+SMA (2026-09-04-059) and a standalone Supertrend
flip (2026-09-04-053); this strategy tests whether the CHOP regime gate
specifically helps the volatility-band-based Supertrend stop-and-reverse
system (as opposed to a plain SMA trend filter), reusing the exact
Supertrend construction from 2026-09-04_supertrend_flip.py.

CHOP formula (standard, Bill Dreiss):
    TR = true range
    CHOP = 100 * log10(sum(TR, n) / (max(High, n) - min(Low, n))) / log10(n)

Signal logic
------------
- Supertrend (ATR-band stop-and-reverse, standard construction) computes a
  boolean bullish/bearish regime flag.
- CHOP(chop_window) < trending_threshold => trending regime (gate open).
- Entry (long): Supertrend flips bullish (fresh bar, was bearish
  yesterday) AND CHOP signals a trending regime at that bar.
- Exit: Supertrend flips bearish, OR CHOP rises above `exit_chop_threshold`
  while in position (regime deteriorates to choppy, an early defensive
  exit), OR a `max_hold_days` time-stop.
- Flat otherwise; long-only, no shorting (per SAFETY.md).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly across a parameter grid).
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


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    return pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)


def _choppiness_index(df: pd.DataFrame, window: int) -> pd.Series:
    tr = _true_range(df)
    tr_sum = tr.rolling(window).sum()
    high_max = df["high"].rolling(window).max()
    low_min = df["low"].rolling(window).min()
    rng = (high_max - low_min).replace(0, pd.NA)
    chop = 100.0 * np.log10(tr_sum / rng) / np.log10(window)
    return chop


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
    st_multiplier: float = 3.0,
    chop_window: int = 14,
    trending_threshold: float = 38.0,
    exit_chop_threshold: float = 62.0,
    max_hold_days: int = 25,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    bullish = _supertrend(df, atr_period=atr_period, multiplier=st_multiplier)
    chop = _choppiness_index(df, chop_window)

    bullish_flip = bullish & (~bullish.shift(1).fillna(False))
    bearish_flip = (~bullish) & (bullish.shift(1).fillna(True))

    trending_regime = chop < trending_threshold
    entry = bullish_flip & trending_regime.fillna(False)
    exit_regime = chop > exit_chop_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(bearish_flip.iloc[i]) or bool(exit_regime.iloc[i]) or held >= max_hold_days:
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
