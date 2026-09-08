"""Strategy: Ehlers Reflex cycle-trough mean-reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per ProRealCode's transcription of John Ehlers' "Reflex: A New Zero-Lag
Indicator" (TASC Feb 2020) (https://www.prorealcode.com/prorealtime-indicators/reflex-and-trendflex-indicators-john-f-ehlers/):
Reflex is the "cycle-synchronized" companion to the already-tested-and-
accepted Trendflex oscillator (2026-09-06-112, accepted SPY only). Both
apply a 2-pole SuperSmoother low-pass filter to price, then measure the
deviation of the filtered series from a `length`-bar window, normalized by
a recursive mean-square (Ehlers' smoothing constants 0.04/0.96) into a
roughly [-2, +2]-range near-zero-lag oscillator. The key construction
difference: Trendflex sums Filt - Filt[count] directly (trend deviation);
Reflex FIRST detrends by subtracting an estimated linear slope
((Filt[Length]-Filt)/Length) before summing the deviations, so Reflex
isolates the CYCLE component while Trendflex isolates the TREND
component -- Ehlers' own stated design intent ("Reflex synchronizes with
the cycle component... Trendflex retains the trend component").

Since Reflex is explicitly a cycle (not trend) oscillator, we test it as a
mean-reversion signal on its own cyclic troughs rather than reusing
Trendflex's zero-line trend-crossing rule (which would misapply a
trend-following interpretation to a cycle-only construction): long entry
when Reflex, having been below an oversold_threshold (cyclic trough, e.g.
-1.0 std devs), crosses back above that threshold (cycle turning up from
an extreme); exit when Reflex crosses above an overbought_threshold
(cycle peak reached) or a max_hold_days time-stop.

First Reflex-family entry in this repo (distinct from Trendflex, its
already-tested trend-following sibling, and from all prior Ehlers
oscillators -- Fisher Transform, MAMA/FAMA, Laguerre RSI, Cyber Cycle --
since Reflex's slope-detrending-before-normalization step is unique to
this indicator).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Position-weighted daily strategy returns (no transaction costs).
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        {0, 1} long/flat position series aligned to price_df.index.
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _reflex(close: pd.Series, length: int) -> pd.Series:
    n = len(close)
    c = close.values

    a1 = math.exp(-1.414 * math.pi / (0.5 * length))
    b1 = 2 * a1 * math.cos(1.414 * math.pi / (0.5 * length))
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3

    filt = [0.0] * n
    reflex = [0.0] * n
    ms = [0.0] * n

    for i in range(n):
        if i <= length:
            filt[i] = c[i]
            continue
        filt[i] = c1 * (c[i] + c[i - 1]) / 2.0 + c2 * filt[i - 1] + c3 * filt[i - 2]

        slope = (filt[i - length] - filt[i]) / length

        s = 0.0
        for count in range(1, length + 1):
            s += (filt[i] + count * slope) - filt[i - count]
        s = s / length

        ms[i] = 0.04 * s * s + 0.96 * ms[i - 1]
        reflex[i] = s / math.sqrt(ms[i]) if ms[i] != 0 else 0.0

    return pd.Series(reflex, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 20,
    oversold_threshold: float = -1.0,
    overbought_threshold: float = 1.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    reflex = _reflex(close, length)

    was_oversold = reflex.shift(1) < oversold_threshold
    entry = was_oversold & (reflex >= oversold_threshold)
    exit_signal = reflex > overbought_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    warmup = min(length * 3, len(close) - 1)
    valid_start = close.index[warmup] if warmup > 0 else None

    for i in range(len(close)):
        if valid_start is not None and close.index[i] < valid_start:
            position.iloc[i] = 0
            continue
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
