"""Strategy: Range Filter [DW] (DonovanWall) trend-following crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-018):
The Range Filter (DonovanWall, popularized via marketcalls.in's Amibroker
port) filters out minor price action to reveal a clearer underlying trend
line via a two-stage EMA-smoothed average absolute-change range, then a
recursive "ratchet" filter that only moves toward price by up to that range
each bar:

    avg_range   = EMA(|src - src[-1]|, sampling_period)
    smooth_rng  = EMA(avg_range, sampling_period*2-1) * range_mult
    filt[t]:
        if src[t] > filt[t-1]:
            filt[t] = filt[t-1]              if src[t]-smooth_rng[t] < filt[t-1]
                       else src[t]-smooth_rng[t]
        else:
            filt[t] = filt[t-1]              if src[t]+smooth_rng[t] > filt[t-1]
                       else src[t]+smooth_rng[t]

A rising-streak counter increments whenever filt rises bar-over-bar (resets
to 0 when it falls); source's long condition requires that streak > 0 AND
close > filt. Adapted the source's original intraday long/short strategy to
a long-only daily-bar signal (per this repo's convention): entry when
close > filt AND the rising-streak counter is positive; exit when the streak
resets to 0 (filt stops rising) or a max_hold_days time-stop. First Range
Filter [DW] strategy in this repo -- a non-ATR-based recursive
ratchet-toward-price construction, distinct from all prior EMA/SMA
crossover, Keltner/Bollinger band, or ATR-trailing-stop constructions.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position series)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _range_filter(close: pd.Series, sampling_period: int, range_mult: float) -> pd.Series:
    """Compute the recursive Range Filter [DW] line."""
    avg_range = close.diff().abs().ewm(span=sampling_period, adjust=False).mean()
    wper = sampling_period * 2 - 1
    smooth_rng = avg_range.ewm(span=wper, adjust=False).mean() * range_mult

    filt = pd.Series(index=close.index, dtype=float)
    prev = close.iloc[0]
    for i in range(len(close)):
        x = close.iloc[i]
        r = smooth_rng.iloc[i]
        if pd.isna(r):
            filt.iloc[i] = x
            prev = x
            continue
        if x > prev:
            candidate = x - r
            prev = prev if candidate < prev else candidate
        else:
            candidate = x + r
            prev = prev if candidate > prev else candidate
        filt.iloc[i] = prev
    return filt


def generate_signals(
    price_df: pd.DataFrame,
    sampling_period: int = 15,
    range_mult: float = 2.5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    filt = _range_filter(close, sampling_period, range_mult)
    filt_delta = filt.diff()

    upward_streak = pd.Series(0, index=close.index, dtype=int)
    streak = 0
    for i in range(len(close)):
        d = filt_delta.iloc[i]
        if pd.isna(d) or d == 0:
            pass  # hold prior streak value
        elif d > 0:
            streak += 1
        else:
            streak = 0
        upward_streak.iloc[i] = streak

    entry = (close > filt) & (upward_streak > 0)
    exit_streak_reset = upward_streak == 0

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_streak_reset.iloc[i]) or held >= max_hold_days:
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
