"""Strategy: True Strength Index (TSI) bullish price/indicator divergence.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-066):
Per Google AI-overview + Quantified Strategies Substack summary (browser_exec
Google SERP fallback; web_search DDGS backend returning "No results found"
this iteration): "A bullish divergence happens when price makes a lower
low, but the TSI makes a higher low. This can suggest that downside
momentum is weakening." TSI (William Blau 1991) is the standard
double-smoothed price-momentum ratio: TSI = 100 * EMA(EMA(diff, long), short)
/ EMA(EMA(|diff|, long), short), default long=25/short=13, bounded roughly
[-100, 100], with a signal line EMA(TSI, 7).

This repo has 7 prior TSI entries (2026-09-04-129, 2026-09-06-137,
2026-09-10-059, 2026-09-14-096, 2026-09-16-063/147, 2026-09-16-168,
2026-09-17-081/087) but ALL of them are threshold/zero-line/signal-line
CROSSOVER triggers or continuous-sizing dials on the TSI LEVEL -- none use
a price-vs-TSI swing-structure DIVERGENCE pattern (a construction already
established elsewhere in this KB for MFI, %B, EMV, OBV, CMF, Elder Bull
Power, Force Index, MACD histogram, RVI -- but never yet applied to TSI).
This iteration fills that specific gap: entry armed when price makes a
lower swing low over a two-window lookback while TSI makes a higher swing
low at the same bar positions, fired on the next TSI-crosses-above-signal
event; exit on the mirror bearish-divergence-armed condition's crossover,
or a fixed time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position series)
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


def _tsi(close: pd.Series, long_period: int, short_period: int, signal_period: int):
    diff = close.diff()
    abs_diff = diff.abs()
    smoothed_diff = diff.ewm(span=long_period, adjust=False).mean().ewm(span=short_period, adjust=False).mean()
    smoothed_abs_diff = abs_diff.ewm(span=long_period, adjust=False).mean().ewm(span=short_period, adjust=False).mean()
    tsi = 100 * smoothed_diff / smoothed_abs_diff.replace(0, np.nan)
    signal = tsi.ewm(span=signal_period, adjust=False).mean()
    return tsi, signal


def generate_signals(
    price_df: pd.DataFrame,
    long_period: int = 25,
    short_period: int = 13,
    signal_period: int = 7,
    swing_window: int = 20,
    divergence_lookback: int = 40,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Bullish divergence precondition: comparing the swing-low bar within the
    most recent `swing_window` vs the swing-low bar within the PRIOR
    `swing_window` (two consecutive non-overlapping windows): price's later
    swing low is LOWER than its earlier swing low, while TSI's value at that
    same later swing-low bar position is HIGHER than at the earlier one.
    Entry armed by that precondition, fires on the next TSI-crosses-above-
    signal-line event within `divergence_lookback` bars. Exit: TSI crossing
    back below signal, or `max_hold_days` time-stop.
    """
    df = _prep(price_df)
    close = df["close"]

    tsi, signal = _tsi(close, long_period, short_period, signal_period)
    above = tsi > signal
    bull_cross = above & (~above.shift(1).fillna(False))
    bear_cross = (~above) & (above.shift(1).fillna(False))

    n = len(close)
    close_v = close.to_numpy()
    tsi_v = tsi.to_numpy()
    w = swing_window

    bullish_divergence_armed = np.zeros(n, dtype=bool)
    for i in range(2 * w, n):
        prev_win_close = close_v[i - 2 * w : i - w]
        curr_win_close = close_v[i - w : i]
        prev_win_tsi = tsi_v[i - 2 * w : i - w]
        curr_win_tsi = tsi_v[i - w : i]
        if np.any(np.isnan(prev_win_close)) or np.any(np.isnan(curr_win_close)):
            continue
        if np.any(np.isnan(prev_win_tsi)) or np.any(np.isnan(curr_win_tsi)):
            continue
        prev_low_i = int(np.argmin(prev_win_close))
        curr_low_i = int(np.argmin(curr_win_close))
        price_lower_low = curr_win_close[curr_low_i] < prev_win_close[prev_low_i]
        tsi_higher_low = curr_win_tsi[curr_low_i] > prev_win_tsi[prev_low_i]
        bullish_divergence_armed[i] = bool(price_lower_low and tsi_higher_low)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    armed_until = -1
    for i in range(n):
        if bullish_divergence_armed[i]:
            armed_until = i + divergence_lookback

        if in_position:
            held = i - entry_idx
            if bool(bear_cross.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if i <= armed_until and bool(bull_cross.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    leverage_cap = kwargs.pop("leverage_cap", 1.0)
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret * leverage_cap
    return strategy_ret
