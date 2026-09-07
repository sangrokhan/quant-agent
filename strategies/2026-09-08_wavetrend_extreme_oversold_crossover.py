"""Strategy: WaveTrend (WT) extreme-zone oversold crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-094):
Per https://strategyquant.com/codebase/wavetrend-wt/, the WaveTrend
oscillator (WT1/WT2, a CCI-style normalized-then-double-EMA-smoothed
momentum oscillator) generates its primary buy signal when WT1 crosses
above WT2, and "the most reliable crossovers occur when both lines are in
extreme territory -- bullish crosses near -60 to -80... often mark the
beginning of significant trending moves." This is the FIRST WaveTrend
strategy in this repo -- distinct from all prior oscillator-crossover
strategies (Stochastic, RSI, CCI, MACD, Fisher Transform, Inverse Fisher
Transform, Vortex, Aroon) since WaveTrend's construction chains a CCI-like
normalization ((AP-ESA)/(0.015*D)) through TWO layers of EMA smoothing
(WT1 = EMA of the normalized CI, WT2 = 4-period EMA of WT1), a distinct
calculation basis from any of those.

Calculation (per source):
    AP  = (High + Low + Close) / 3                       (HLC3)
    ESA = EMA(AP, channel_length)
    D   = EMA(|AP - ESA|, channel_length)
    CI  = (AP - ESA) / (0.015 * D)
    WT1 = EMA(CI, average_length)
    WT2 = EMA(WT1, 4)

Signal logic
------------
- Entry (long): WT1 crosses from <=WT2 to >WT2 (bullish crossover) while
  WT2 was in oversold extreme territory (WT2 <= oversold_level, default
  -60, at the crossing bar) -- the source's own "most reliable" extreme
  crossover subset, rather than every zero-noise crossover.
- Exit: WT1 crosses back below WT2 (bearish crossover), or a
  max_hold_days time-stop.
- Flat otherwise.

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


def _wavetrend(df: pd.DataFrame, channel_length: int, average_length: int):
    high, low, close = df["high"], df["low"], df["close"]
    ap = (high + low + close) / 3.0
    esa = ap.ewm(span=channel_length, adjust=False).mean()
    d = (ap - esa).abs().ewm(span=channel_length, adjust=False).mean()
    ci = (ap - esa) / (0.015 * d.replace(0, float("nan")))
    ci = ci.fillna(0.0)
    wt1 = ci.ewm(span=average_length, adjust=False).mean()
    wt2 = wt1.ewm(span=4, adjust=False).mean()
    return wt1, wt2


def generate_signals(
    price_df: pd.DataFrame,
    channel_length: int = 10,
    average_length: int = 21,
    oversold_level: float = -60.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    wt1, wt2 = _wavetrend(df, channel_length, average_length)

    wt1_prev = wt1.shift(1)
    wt2_prev = wt2.shift(1)
    cross_up = (wt1_prev <= wt2_prev) & (wt1 > wt2)
    cross_down = (wt1_prev > wt2_prev) & (wt1 <= wt2)

    entry = cross_up & (wt2 <= oversold_level)
    exit_cross = cross_down

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or held >= max_hold_days:
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
