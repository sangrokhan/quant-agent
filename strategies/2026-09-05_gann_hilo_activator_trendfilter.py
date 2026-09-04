"""Strategy: Gann HiLo Activator state-flip trend entry, gated by a longer SMA
trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-017):
The Gann HiLo Activator (W.D. Gann concept, popularized by Robert Krausz) is a
stepped trailing support/resistance line built from two simple moving
averages of High and Low:
    HMA(n) = SMA(High, n)
    LMA(n) = SMA(Low, n)
State machine (per trendsandbreakouts.com's rule disclosure):
    - If close > prior-bar HMA(n): state = "up"
    - If close < prior-bar LMA(n): state = "down"
    - Otherwise: keep prior state
    - Plotted line = LMA(n) when state == "up" (support), HMA(n) when
      state == "down" (resistance)

Standalone HiLo-flip strategies (Parabolic SAR id=2026-09-04-042, SuperTrend
id=2026-09-03-014) in this repo needed a longer-term SMA trend filter to
avoid whipsaws in choppy regimes -- applying the same pattern here: only take
the long entry (state flips from "down" to "up") when close is already above
a slower SMA(trend_window) trend filter, and exit on the reverse state flip,
the trend filter breaking, or a max_hold_days time-stop. First Gann HiLo
Activator strategy in this repo -- distinct from the flip-only variant tested
at id=2026-09-04-128 (rejected) by adding this SMA trend gate, and
structurally distinct from Parabolic SAR/SuperTrend (different construction:
SMA-of-high/low state switch rather than ATR-banded stop-and-reverse).

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


def _gann_hilo_state(df: pd.DataFrame, hilo_period: int) -> pd.Series:
    """Return the Gann HiLo Activator trend state as a {-1, +1} series
    (+1 = "up" state / line plots LMA support, -1 = "down" state / line
    plots HMA resistance). Uses the PRIOR bar's HMA/LMA for the comparison
    (per source's rule) to avoid look-ahead."""
    hma = df["high"].rolling(hilo_period).mean()
    lma = df["low"].rolling(hilo_period).mean()
    prior_hma = hma.shift(1)
    prior_lma = lma.shift(1)

    state = pd.Series(index=df.index, dtype=float)
    prev_state = 1  # arbitrary initial state; warms up during rolling window
    for i in range(len(df)):
        c = df["close"].iloc[i]
        ph = prior_hma.iloc[i]
        pl = prior_lma.iloc[i]
        if pd.isna(ph) or pd.isna(pl):
            state.iloc[i] = float("nan")
            continue
        if c > ph:
            prev_state = 1
        elif c < pl:
            prev_state = -1
        state.iloc[i] = prev_state
    return state


def generate_signals(
    price_df: pd.DataFrame,
    hilo_period: int = 3,
    trend_window: int = 100,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    state = _gann_hilo_state(df, hilo_period)
    flip_up = (state == 1) & (state.shift(1) == -1)

    sma_trend = close.rolling(trend_window).mean()
    trend_ok = close > sma_trend

    entry = flip_up & trend_ok.fillna(False)
    exit_flip_down = (state == -1) & (state.shift(1) == 1)
    exit_trend_break = ~trend_ok.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_flip_down.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
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
