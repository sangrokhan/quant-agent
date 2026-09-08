"""Strategy: Elder Triple Screen (weekly-MACD-histogram trend + daily Force Index pullback).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-007):
Alexander Elder's Triple Screen system uses a longer timeframe's
trend-following indicator to establish direction, then a shorter timeframe's
oscillator to time entries against brief pullbacks within that trend. Per a
Google-surfaced snippet of the "Alexander Elder Triple Screen Trading
System" reference PDF: "When the weekly MACD-Histogram rises, [look for] the
2-day EMA of Force Index [to dip negative, signaling a pullback-buy]" --
i.e. long entry when the longer-timeframe MACD-Histogram is rising (bullish
trend established) AND the short-timeframe Force Index (volume-weighted
price-change momentum) dips below zero then recovers (a brief
pullback/dip-buy within the uptrend, not a trend reversal).

Since this repo's data loaders are daily-only (no native weekly resample),
the "weekly" trend screen is approximated with a longer-period MACD
(macd_fast/macd_slow/macd_signal roughly 5x the classic daily 12/26/9,
i.e. ~60/130/45) applied directly to daily closes -- a longer effective
lookback playing the same "slower timeframe trend filter" role the source's
weekly chart plays relative to a daily entry chart. First Elder Triple
Screen strategy in this repo.

Signal logic
------------
- MACD-Histogram (macd_fast, macd_slow, macd_signal, default longer-period
  60/130/45 to proxy "weekly" trend on daily bars): rising when
  histogram[t] > histogram[t-1].
- Force Index: volume * (close - close.shift(1)), smoothed by a
  force_index_ema-period EMA (default 2, per source's "2-day EMA of Force
  Index").
- Entry (long): MACD-Histogram is positive AND rising (bullish trend
  screen) AND Force Index(EMA) crosses from <=0 up to >0 (pullback
  recovering, entry-timing screen).
- Exit: MACD-Histogram turns negative or stops rising (trend screen
  breaks), OR Force Index(EMA) turns sharply negative again beyond
  exit_force_thresh, OR max_hold_days elapses.

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


def _macd_histogram(close: pd.Series, fast: int, slow: int, signal: int) -> pd.Series:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line - signal_line


def _force_index(df: pd.DataFrame, ema_window: int) -> pd.Series:
    close = df["close"]
    volume = df["volume"]
    raw_force = volume * close.diff()
    return raw_force.ewm(span=ema_window, adjust=False).mean()


def generate_signals(
    price_df: pd.DataFrame,
    macd_fast: int = 60,
    macd_slow: int = 130,
    macd_signal: int = 45,
    force_index_ema: int = 2,
    exit_force_thresh_mult: float = 2.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    hist = _macd_histogram(close, macd_fast, macd_slow, macd_signal)
    hist_rising = hist > hist.shift(1)
    trend_bullish = (hist > 0) & hist_rising

    force = _force_index(df, force_index_ema)
    force_prev = force.shift(1)
    force_recover = (force_prev <= 0) & (force > 0)

    force_std = force.rolling(60, min_periods=20).std()
    exit_force_thresh = -exit_force_thresh_mult * force_std

    entry_signal = trend_bullish & force_recover
    exit_trend_break = ~trend_bullish
    exit_force_spike = force < exit_force_thresh

    close_vals = close.values
    entry_sig_vals = entry_signal.fillna(False).values
    exit_trend_vals = exit_trend_break.fillna(True).values
    exit_force_vals = exit_force_spike.fillna(False).values

    n = len(close_vals)
    position_vals = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_trend_vals[i]) or bool(exit_force_vals[i]) or held >= max_hold_days:
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
