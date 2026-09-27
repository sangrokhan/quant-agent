"""Strategy: N-day high breakout confirmed by a rising, positive Percentage
Volume Oscillator (PVO).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-107),
sourced from:
  - StockCharts ChartSchool "Percentage Volume Oscillator (PVO)"
    (https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/percentage-volume-oscillator-pvo,
    visited this iteration): "The Percentage Volume Oscillator (PVO) can be
    used to confirm a support or resistance break... A resistance break on
    expanding volume shows more buying interest, increasing the chances of
    success... [example] VLO was still stuck in the pennant on the first PVO
    cross, but broke pennant resistance with the second PVO cross. Volume
    confirmed the breakout and VLO continued its advance." Formula (source's
    own, matches MACD/PPO construction exactly):
        PVO = ((12-day EMA of Volume - 26-day EMA of Volume) / 26-day EMA of
               Volume) * 100
        Signal Line = 9-day EMA of PVO
        PVO-Histogram = PVO - Signal Line

This is the first PVO-family strategy in this repo (0 prior KB hits for
"PVO"/"Percentage Volume Oscillator" as of this iteration, unlike the
heavily saturated OBV/CMF/MFI/Klinger volume-indicator families). The
breakout side (N-day high) has ample repo precedent (Donchian breakout,
52wk-high momentum) but has not previously been gated specifically on a
PVO(12,26,9) rising-and-positive volume-confirmation condition, which is
this source's own explicitly disclosed use case for PVO.

Signal logic
------------
- Breakout trigger: close crosses above the highest close of the prior
  breakout_window days (Donchian-style, using close not high, to stay
  consistent with existing repo breakout conventions).
- Volume confirmation (per source): PVO(fast=12, slow=26) > 0 (12-day Volume
  EMA above 26-day Volume EMA, i.e. volume already above its own recent
  average) AND PVO is rising (PVO[t] > PVO[t-1], i.e. volume momentum is
  still increasing, not just historically elevated) -- operationalizing the
  source's "PVO moved into positive territory with a sharp surge... Volume
  confirmed the breakout" pattern.
- Long entry: breakout trigger AND volume confirmation, both true on the
  same bar.
- Exit: close falls back below the trailing SMA(exit_window) (mean-recross
  exit, standard repo convention for breakout strategies), or a
  max_hold_days time-stop.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, position lagged by 1 day to avoid look-ahead bias)
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


def _pvo(volume: pd.Series, fast: int, slow: int, signal: int) -> pd.Series:
    vol_fast = volume.ewm(span=fast, adjust=False, min_periods=fast).mean()
    vol_slow = volume.ewm(span=slow, adjust=False, min_periods=slow).mean()
    pvo = ((vol_fast - vol_slow) / vol_slow.replace(0, np.nan)) * 100.0
    return pvo


def generate_signals(
    price_df: pd.DataFrame,
    breakout_window: int = 20,
    pvo_fast: int = 12,
    pvo_slow: int = 26,
    pvo_signal: int = 9,
    exit_window: int = 20,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    highest_close = close.shift(1).rolling(breakout_window, min_periods=breakout_window).max()
    breakout = close > highest_close

    pvo = _pvo(volume, pvo_fast, pvo_slow, pvo_signal)
    pvo_positive = pvo > 0
    pvo_rising = pvo > pvo.shift(1)
    volume_confirmed = pvo_positive & pvo_rising

    entry_signal = (breakout & volume_confirmed).fillna(False)

    exit_sma = close.rolling(exit_window, min_periods=exit_window).mean()
    exit_signal = close < exit_sma

    entry_arr = entry_signal.to_numpy()
    exit_arr = exit_signal.fillna(False).to_numpy()
    pos_arr = np.zeros(len(df), dtype=int)

    in_position = False
    hold_days = 0
    for i in range(len(df)):
        if in_position:
            hold_days += 1
            if exit_arr[i] or hold_days >= max_hold_days:
                in_position = False
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_arr[i]:
                in_position = True
                hold_days = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    position = pd.Series(pos_arr, index=df.index, dtype=int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    breakout_window: int = 20,
    pvo_fast: int = 12,
    pvo_slow: int = 26,
    pvo_signal: int = 9,
    exit_window: int = 20,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return the strategy's daily return series (position lagged 1 day)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        breakout_window=breakout_window,
        pvo_fast=pvo_fast,
        pvo_slow=pvo_slow,
        pvo_signal=pvo_signal,
        exit_window=exit_window,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
