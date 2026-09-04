"""Strategy: WaveTrend (WT1/WT2) signal-line crossover, LazyBear formulation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-145):
The WaveTrend oscillator (WT1 = smoothed CCI-like channel index, WT2 = its
4-period SMA signal line) generates a long entry when WT1 crosses above WT2
while both are below an oversold threshold (extreme -60 zone), signalling a
momentum shift out of an oversold trough. Exit when WT1 crosses back below
WT2, or WT1 rises above an overbought threshold (extreme +60, take profit /
avoid chasing extended moves), or after a max_hold_days time-stop. Per
StrategyQuant/LazyBear WaveTrend explainer (source URL in notes). Distinct
from CCI, Stochastic %K/%D, and StochRSI already tested in this repo -- WT1
is a double-smoothed CCI-like construct crossed against its own SMA signal
line, closer to a MACD-style dual-line crossover than a raw CCI threshold
rule.

Signal logic
------------
- AP (average price) = HLC3 = (High + Low + Close) / 3
- ESA = EMA(AP, channel_len)
- D = EMA(|AP - ESA|, channel_len)
- CI = (AP - ESA) / (0.015 * D)
- WT1 = EMA(CI, avg_len)
- WT2 = SMA(WT1, 4)
- Entry (long): WT1 crosses above WT2 AND WT1 <= oversold_threshold (deep
  extreme, e.g. -60) at the crossover bar.
- Exit: WT1 crosses below WT2, OR WT1 >= overbought_threshold (e.g. +60),
  OR max_hold_days elapsed since entry.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
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


def _wavetrend(df: pd.DataFrame, channel_len: int, avg_len: int) -> tuple[pd.Series, pd.Series]:
    ap = (df["high"] + df["low"] + df["close"]) / 3.0
    esa = ap.ewm(span=channel_len, adjust=False).mean()
    d = (ap - esa).abs().ewm(span=channel_len, adjust=False).mean()
    d = d.replace(0.0, np.nan)
    ci = (ap - esa) / (0.015 * d)
    ci = ci.fillna(0.0)
    wt1 = ci.ewm(span=avg_len, adjust=False).mean()
    wt2 = wt1.rolling(4).mean()
    return wt1, wt2


def generate_signals(
    price_df: pd.DataFrame,
    channel_len: int = 10,
    avg_len: int = 21,
    oversold_threshold: float = -60.0,
    overbought_threshold: float = 60.0,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    wt1, wt2 = _wavetrend(df, channel_len, avg_len)

    cross_up = (wt1 > wt2) & (wt1.shift(1) <= wt2.shift(1))
    cross_down = (wt1 < wt2) & (wt1.shift(1) >= wt2.shift(1))

    entry_raw = cross_up & (wt1 <= oversold_threshold)
    exit_signal_raw = cross_down | (wt1 >= overbought_threshold)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_days = 0
    entry_arr = entry_raw.to_numpy()
    exit_arr = exit_signal_raw.to_numpy()
    pos_arr = position.to_numpy().copy()

    for i in range(len(df)):
        if in_pos:
            hold_days += 1
            if exit_arr[i] or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_arr[i]:
                in_pos = True
                hold_days = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    position = pd.Series(pos_arr, index=df.index, dtype=int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    channel_len: int = 10,
    avg_len: int = 21,
    oversold_threshold: float = -60.0,
    overbought_threshold: float = 60.0,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        channel_len=channel_len,
        avg_len=avg_len,
        oversold_threshold=oversold_threshold,
        overbought_threshold=overbought_threshold,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
