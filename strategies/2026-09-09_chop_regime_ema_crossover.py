"""Strategy: Choppiness Index regime gate + fast/slow EMA crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-008):
The Choppiness Index (CHOP, Bill Dreiss) is a non-directional 0-100 regime
classifier: low CHOP indicates a trending market, high CHOP indicates a
choppy/ranging market. Per StrategyQuant's Codebase confirmation
(https://strategyquant.com/codebase/choppiness-index/) of the standard
formula and the widely-cited Fibonacci-derived convention (CHOP<38.2 =
trending, CHOP>61.8 = choppy), gating entries to only the trending regime
should improve a fast/slow EMA crossover's signal quality by avoiding
whipsaw trades during range-bound chop.

This repo's prior CHOP entry (2026-09-04-059) combined CHOP<38 with a
STATIC close>SMA directional filter (a binary "are we above the average"
check). This iteration instead gates an EMA CROSSOVER (a distinct
confirmation/timing mechanism -- crossover timing vs a static directional
threshold) on the CHOP regime, testing whether the more responsive
crossover entry, restricted to CHOP's low-chop regime, changes the
risk/reward profile enough to pass validators.

Signal logic
------------
- CHOP(chop_window): 100*log10(sum(ATR(1), chop_window) / (max_high -
  min_low)) / log10(chop_window).
- Trending regime: CHOP < chop_trend_thresh (default 38.2).
- Fast/slow EMA crossover (ema_fast, ema_slow): entry when EMA_fast crosses
  above EMA_slow WHILE in the trending regime.
- Exit: EMA_fast crosses back below EMA_slow, OR CHOP rises above
  chop_choppy_thresh (default 61.8, regime turns choppy -- risk-off exit),
  OR max_hold_days elapses.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr1(df: pd.DataFrame) -> pd.Series:
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
    return tr


def _choppiness_index(df: pd.DataFrame, window: int) -> pd.Series:
    atr1 = _atr1(df)
    sum_atr = atr1.rolling(window).sum()
    max_high = df["high"].rolling(window).max()
    min_low = df["low"].rolling(window).min()
    rng = (max_high - min_low).replace(0, float("nan"))
    chop = 100.0 * np.log10(sum_atr / rng) / np.log10(window)
    return chop


def generate_signals(
    price_df: pd.DataFrame,
    chop_window: int = 14,
    chop_trend_thresh: float = 38.2,
    chop_choppy_thresh: float = 61.8,
    ema_fast: int = 10,
    ema_slow: int = 30,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    chop = _choppiness_index(df, chop_window)
    trending_regime = chop < chop_trend_thresh
    choppy_regime = chop > chop_choppy_thresh

    ema_f = close.ewm(span=ema_fast, adjust=False).mean()
    ema_s = close.ewm(span=ema_slow, adjust=False).mean()
    bull_cross = (ema_f.shift(1) <= ema_s.shift(1)) & (ema_f > ema_s)
    bear_cross = (ema_f.shift(1) >= ema_s.shift(1)) & (ema_f < ema_s)

    entry_signal = bull_cross & trending_regime.fillna(False)

    close_vals = close.values
    entry_sig_vals = entry_signal.fillna(False).values
    bear_cross_vals = bear_cross.fillna(False).values
    choppy_vals = choppy_regime.fillna(False).values

    n = len(close_vals)
    position_vals = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(bear_cross_vals[i]) or bool(choppy_vals[i]) or held >= max_hold_days:
                in_position = False
                position_vals[i] = 0
                continue
            position_vals[i] = 1
        else:
            if bool(entry_sig_vals[i]):
                in_position = True
                entry_idx = i
                position_vals[i] = 1
            else:
                position_vals[i] = 0

    return pd.Series(position_vals, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
