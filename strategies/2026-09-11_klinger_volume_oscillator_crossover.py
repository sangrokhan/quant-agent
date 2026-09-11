"""Strategy: Klinger Volume Oscillator (KVO) signal-line crossover, trend-gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-122):
Sources:
  https://lightningchart.com/blog/trader/klinger-volume-oscillator/
  https://www.investopedia.com/terms/k/klingeroscillator.asp
Stephen Klinger's Volume Force (VF) indicator combines volume, high-low
range, and a +1/-1 trend-direction sign into a single "volume pressure"
series; the Klinger Oscillator (KO) = short-period EMA(VF) - long-period
EMA(VF) (defaults 34/55), smoothed by a signal line = N-period EMA(KO,
default 13). Per both sources' explicit trading rule: a bullish crossover
(KO crosses above its signal line) indicates short-term volume
accumulation accelerating relative to the longer-term trend -> long entry;
a bearish crossover (KO crosses below signal) -> exit/short. This repo
gates the raw crossover with a trend filter (close > SMA(trend_window))
since 2026-09-08-097 previously found Klinger interesting but untested
(no novel-candidate note only referenced it as already covered elsewhere
-- verified via fresh Stage-1 index search this iteration that no entry
actually implements/tests Klinger itself). First Klinger Volume Oscillator
strategy in this repo, distinct from all prior volume-flow indicators
(Chaikin Money Flow, Twiggs Money Flow, PVT, OBV, PVO) via its unique
trend-sign-weighted Volume Force construction and dual-EMA-of-VF signal.

Signal logic
------------
- Volume Force (VF): T = +1 if (H+L+C) > prior (H+L+C) else -1;
  dm = H - L; cm accumulates dm while T stays the same as prior T, resets
  to (prior dm + current dm) when T flips; VF = V * (2*((dm/cm)-1)) * T * 100
  (cm floored away from zero to avoid div-by-zero).
- KO = EMA(VF, short_period) - EMA(VF, long_period)
- Signal = EMA(KO, signal_period)
- Entry (long): KO crosses from <= Signal to > Signal AND close > SMA(trend_window)
- Exit (flat): KO crosses from > Signal to <= Signal, OR trend filter breaks
  (close <= SMA(trend_window)), OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _volume_force(df: pd.DataFrame) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"].fillna(0.0)

    hlc = high + low + close
    hlc_prev = hlc.shift(1)
    trend = pd.Series(np.where(hlc > hlc_prev, 1.0, -1.0), index=df.index)
    trend.iloc[0] = 1.0

    dm = high - low

    dm_vals = dm.to_numpy()
    trend_vals = trend.to_numpy()
    cm_vals = np.empty(len(df))
    prev_cm = dm_vals[0] if len(dm_vals) else 0.0
    prev_trend = trend_vals[0] if len(trend_vals) else 1.0
    for i in range(len(df)):
        t = trend_vals[i]
        d = dm_vals[i]
        if i == 0:
            c = d
        elif t == prev_trend:
            c = prev_cm + d
        else:
            c = dm_vals[i - 1] + d
        cm_vals[i] = c
        prev_cm = c
        prev_trend = t
    cm = pd.Series(cm_vals, index=df.index)

    cm_safe = cm.replace(0.0, np.nan)
    vf = volume * (2.0 * ((dm / cm_safe) - 1.0)) * trend * 100.0
    return vf.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    short_period: int = 34,
    long_period: int = 55,
    signal_period: int = 13,
    trend_window: int = 100,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    vf = _volume_force(df)
    ko = vf.ewm(span=short_period, adjust=False).mean() - vf.ewm(span=long_period, adjust=False).mean()
    signal = ko.ewm(span=signal_period, adjust=False).mean()

    sma_trend = close.rolling(trend_window).mean()
    trend_ok = close > sma_trend

    above = ko > signal
    cross_up = above & (~above.shift(1).fillna(False))
    cross_down = (~above) & (above.shift(1).fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or not bool(trend_ok.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]) and bool(trend_ok.iloc[i]):
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
