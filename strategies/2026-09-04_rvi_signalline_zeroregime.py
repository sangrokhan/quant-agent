"""Strategy: Relative Vigor Index (RVI) signal-line crossover, zero-line
regime-confirmed.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-147):
RVI compares each bar's close-vs-open push, normalized by the bar's
high-low range (v_t = (Close-Open)/(High-Low)), then smooths it with an
SMA(n) to form the RVI line and a further SMA(m) of that to form the signal
line. Per trendsandbreakouts.com's explainer, a bullish signal-line
crossover (RVI crosses above signal) indicates improving vigor, and the
zero line acts as a regime divider (crossovers near zero are noisier than
those confirmed by an above-zero regime). This strategy: long entry when
RVI crosses above its signal line while RVI > 0 (regime-confirmed, avoiding
the noisy near-zero crossovers the source warns about); exit on the
opposite crossover (RVI crosses below signal), RVI dropping below zero, or
a max_hold_days time-stop. Distinct from Balance of Power (already tested,
similar close-vs-open concept but no double-smoothed signal-line
crossover) and other oscillator-crossover strategies already in this repo.

Signal logic
------------
- v_t = (Close - Open) / (High - Low), with 0 substituted when High==Low.
- RVI = SMA(v_t, rvi_period)  [default 10]
- Signal = SMA(RVI, signal_period)  [default 4]
- Entry (long): RVI crosses above Signal AND RVI > 0 at the crossover bar.
- Exit: RVI crosses below Signal, OR RVI <= 0, OR max_hold_days elapsed.
- Flat otherwise.
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


def _rvi(df: pd.DataFrame, rvi_period: int, signal_period: int) -> tuple[pd.Series, pd.Series]:
    rng = (df["high"] - df["low"]).replace(0.0, np.nan)
    v = (df["close"] - df["open"]) / rng
    v = v.fillna(0.0)
    rvi = v.rolling(rvi_period).mean()
    signal = rvi.rolling(signal_period).mean()
    return rvi, signal


def generate_signals(
    price_df: pd.DataFrame,
    rvi_period: int = 10,
    signal_period: int = 4,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    rvi, signal = _rvi(df, rvi_period, signal_period)

    cross_up = (rvi > signal) & (rvi.shift(1) <= signal.shift(1))
    cross_down = (rvi < signal) & (rvi.shift(1) >= signal.shift(1))

    entry_raw = (cross_up & (rvi > 0)).fillna(False).to_numpy()
    exit_raw = (cross_down | (rvi <= 0)).fillna(True).to_numpy()

    pos_arr = [0] * len(df)
    in_pos = False
    hold_days = 0
    for i in range(len(df)):
        if in_pos:
            hold_days += 1
            if exit_raw[i] or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_raw[i]:
                in_pos = True
                hold_days = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    rvi_period: int = 10,
    signal_period: int = 4,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        rvi_period=rvi_period,
        signal_period=signal_period,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
