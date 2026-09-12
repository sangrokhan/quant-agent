"""Strategy: Ehlers Reflex (cycle-synchronized zero-lag oscillator),
zero-line crossover, gated to cyclical (non-trending) regimes.

Hypothesis (see knowledge_base id 2026-09-12-177):
Per John F. Ehlers' "Reflex: A New Zero-Lag Indicator" (TASC February 2020
Traders' Tips), full formula transcribed at
https://www.prorealcode.com/prorealtime-indicators/reflex-and-trendflex-indicators-john-f-ehlers/:
a SuperSmoother-filtered price series has a `Length`-bar-ahead linear
extrapolation slope computed, then the SUM of (extrapolated - actual
lagged filter values) over the window measures how far actual filtered
price deviates from the extrapolated trend line -- capturing cyclical
(non-trend) motion. This sum is normalized by a recursive mean-square
(0.04/0.96 smoothing, Ehlers' own EWMA-style variance tracker) to produce
a standard-deviation-normalized oscillator. Per the source: "The Reflex
indicator synchronizes with the cycle component in the price data" (as
opposed to its "companion" Trendflex, which "retains the trend
component" -- Trendflex already tested/accepted in this repo at
2026-09-06-112).

Since Reflex specifically tracks the CYCLE component, this strategy treats
it as a cyclical/ranging-market oscillator: long entry when Reflex crosses
from negative to positive (cycle turning up), exit on the reverse cross
or a max_hold_days time-stop, gated by an ADX-based non-trending regime
filter (reusing this repo's standard Wilder ADX helper) since a
cycle-synchronized oscillator is conceptually meant for ranging conditions
rather than strong trends (mirroring the same regime-appropriateness logic
already applied to the Reversion Index, 2026-09-12-172).

First standalone Ehlers Reflex strategy in this repo -- distinct from
Trendflex (2026-09-06-112, accepted SPY-only, extracts the TREND component
via a plain running-difference sum with no forward slope-extrapolation
term) since Reflex's slope-extrapolated deviation construction is
mathematically different (isolates cyclical, not trend, motion) despite
sharing the same SuperSmoother pre-filter and mean-square normalization.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _reflex(close: pd.Series, length: int) -> pd.Series:
    """Ehlers' Reflex indicator (per TASC Feb 2020 formula, full transcription
    at prorealcode.com)."""
    a1 = math.exp(-1.414 * math.pi / (0.5 * length))
    b1 = 2 * a1 * math.cos(1.414 * math.pi / (0.5 * length))
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3

    values = close.to_numpy()
    n = len(values)
    filt = np.zeros(n)
    for i in range(1, n):
        if i < 2:
            filt[i] = values[i]
            continue
        filt[i] = c1 * (values[i] + values[i - 1]) / 2.0 + c2 * filt[i - 1] + c3 * filt[i - 2]

    reflex = np.zeros(n)
    ms = 0.0
    for i in range(length, n):
        slope = (filt[i - length] - filt[i]) / length
        total = 0.0
        for count in range(1, length + 1):
            total += (filt[i] + count * slope) - filt[i - count]
        total /= length
        ms = 0.04 * total * total + 0.96 * ms
        reflex[i] = total / math.sqrt(ms) if ms > 0 else 0.0

    return pd.Series(reflex, index=close.index)


def _wilder_smooth(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(0.0, index=high.index)
    minus_dm = pd.Series(0.0, index=high.index)
    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move[(up_move > down_move) & (up_move > 0)]
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move[(down_move > up_move) & (down_move > 0)]

    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    atr = _wilder_smooth(tr, period)
    plus_dm_smooth = _wilder_smooth(plus_dm, period)
    minus_dm_smooth = _wilder_smooth(minus_dm, period)

    plus_di = 100.0 * (plus_dm_smooth / atr.replace(0, pd.NA))
    minus_di = 100.0 * (minus_dm_smooth / atr.replace(0, pd.NA))

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)
    adx = _wilder_smooth(dx.fillna(0.0), period)
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 20,
    adx_period: int = 14,
    range_max_adx: float = 25.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]
    n = len(close)

    reflex = _reflex(close, length)
    adx = _adx(high, low, close, adx_period)
    ranging = (adx < range_max_adx).fillna(False)

    cross_up = (reflex > 0) & (reflex.shift(1) <= 0)
    cross_down = (reflex < 0) & (reflex.shift(1) >= 0)
    entry = (cross_up & ranging).fillna(False)
    exit_signal = cross_down.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
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

    return position


def generate_returns(
    price_df: pd.DataFrame,
    length: int = 20,
    adx_period: int = 14,
    range_max_adx: float = 25.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs here)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        length=length,
        adx_period=adx_period,
        range_max_adx=range_max_adx,
        max_hold_days=max_hold_days,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    return strat_returns
