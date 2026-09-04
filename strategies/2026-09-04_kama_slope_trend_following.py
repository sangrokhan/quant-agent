"""Strategy: Kaufman Adaptive Moving Average (KAMA) slope trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-151):
KAMA (Perry Kaufman, 1995) dynamically adjusts its smoothing constant via
an Efficiency Ratio (ER = |close - close[n bars ago]| / sum of bar-to-bar
absolute changes over n bars), so it hugs price tightly during efficient
trends and flattens during choppy/noisy ranges. Per ArrowAlgo's guide, the
trend-following approach is: enter long when KAMA begins sloping upward AND
price is above KAMA (confirms a genuine efficient trend, not noise); exit
when KAMA flattens or turns down, or price closes back below KAMA. This
strategy operationalizes that directly, plus a max_hold_days time-stop.
First KAMA strategy in this repo -- distinct from other adaptive/smoothing
MAs (ZLEMA, VWMA, T3, Hull already tested) since KAMA's smoothing constant
is dynamically derived from an efficiency ratio of trend-vs-noise rather
than a fixed weighting scheme.

Signal logic
------------
- ER[t] = |close[t] - close[t-er_window]| / sum(|close[i]-close[i-1]|
  for i in the er_window) -- 0 to 1, near 1 = efficient trend.
- SC[t] = (ER[t] * (fast_sc - slow_sc) + slow_sc) ** 2, fast_sc = 2/(2+1),
  slow_sc = 2/(slow_period+1).
- KAMA[t] = KAMA[t-1] + SC[t] * (close[t] - KAMA[t-1]), seeded with the
  first close.
- KAMA slope = KAMA[t] - KAMA[t - slope_window].
- Entry (long): KAMA slope > 0 AND close > KAMA (both conditions confirm
  a genuine upward, efficient trend).
- Exit: KAMA slope <= 0, OR close < KAMA, OR max_hold_days elapsed.
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


def _kama(close: pd.Series, er_window: int, fast_period: int, slow_period: int) -> pd.Series:
    change = (close - close.shift(er_window)).abs()
    volatility = close.diff().abs().rolling(er_window).sum()
    er = (change / volatility.replace(0.0, np.nan)).fillna(0.0)

    fast_sc = 2.0 / (fast_period + 1)
    slow_sc = 2.0 / (slow_period + 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

    kama = np.empty(len(close))
    kama[:] = np.nan
    close_arr = close.to_numpy()
    sc_arr = sc.to_numpy()

    first_valid = er_window
    if first_valid >= len(close):
        return pd.Series(kama, index=close.index)
    kama[first_valid] = close_arr[first_valid]
    for i in range(first_valid + 1, len(close)):
        prev = kama[i - 1]
        if np.isnan(prev):
            kama[i] = close_arr[i]
        else:
            kama[i] = prev + sc_arr[i] * (close_arr[i] - prev)

    return pd.Series(kama, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    er_window: int = 10,
    fast_period: int = 2,
    slow_period: int = 30,
    slope_window: int = 5,
    max_hold_days: int = 30,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    kama = _kama(close, er_window, fast_period, slow_period)
    slope = kama - kama.shift(slope_window)

    entry_raw = ((slope > 0) & (close > kama)).fillna(False).to_numpy()
    exit_raw = ((slope <= 0) | (close < kama)).fillna(True).to_numpy()

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
    er_window: int = 10,
    fast_period: int = 2,
    slow_period: int = 30,
    slope_window: int = 5,
    max_hold_days: int = 30,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        er_window=er_window,
        fast_period=fast_period,
        slow_period=slow_period,
        slope_window=slope_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
