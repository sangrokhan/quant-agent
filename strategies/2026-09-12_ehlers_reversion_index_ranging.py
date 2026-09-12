"""Strategy: Ehlers Reversion Index (mean reversion, peaks/valleys via
Trigger/Smooth crossover), gated to ranging (non-trending) regimes.

Hypothesis (see knowledge_base id 2026-09-12-172):
Per John F. Ehlers' "Identifying Peaks And Valleys In Ranging Markets"
(TASC January 2026 Traders' Tips), implemented at
https://www.tradingview.com/script/V35NeC45-TASC-2026-01-The-Reversion-Index/
(full concept disclosure): the raw Reversion Index is the net price change
over a `length`-bar window, normalized by the sum of absolute price changes
over the same window (a "how directional was this move, on a -1..+1
scale" measure closely related to Kaufman's Efficiency Ratio's numerator
construction but SIGNED, not absolute). The raw index is smoothed with a
2-pole SuperSmoother (Ehlers' own default length=8) to form "Smooth"; a
"Trigger" line is the same smoothing applied at HALF that period (length=4)
to lead Smooth. Per the source's own USAGE section: "peaks and valleys are
interpreted as the cross of the Trigger and Smooth lines" -- i.e. Trigger
crossing above Smooth marks a valley (price turning up, buy), Trigger
crossing below Smooth marks a peak (price turning down, sell/exit). The
source explicitly frames this as a RANGING-MARKET indicator (mean
reversion), not a trend indicator -- so this implementation adds a
`range_max_adx` gate (ADX below a threshold = non-trending regime, reusing
this repo's standard Wilder ADX helper) to trade the signal only when the
source's own stated regime assumption (ranging, not trending) plausibly
holds, rather than firing it unconditionally across all regimes.

First Ehlers Reversion Index strategy in this repo -- distinct from all
other Ehlers-family entries already tested (Instantaneous Trendline, Cyber
Cycle, Even Better Sinewave, Voss Predictive Filter, Deviation-Scaled
MA/Oscillator, Trendflex, Roofing Filter, Correlation Cycle, SuperSmoother-
as-baseline, Precision Trend) via its signed-net-change/sum-abs-change
normalization and Trigger/Smooth (half-vs-full smoothing period)
lead/lag-crossover mechanic, explicitly targeted at ranging markets rather
than trend continuation.

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


def _supersmoother(data: pd.Series, period: int) -> pd.Series:
    """Ehlers' standard 2-pole SuperSmoother low-pass filter."""
    a1 = math.exp(-1.414 * math.pi / period)
    b1 = 2 * a1 * math.cos(1.414 * math.pi / period)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3

    values = data.to_numpy()
    n = len(values)
    filt = np.zeros(n)
    for i in range(2, n):
        filt[i] = c1 * (values[i] + values[i - 1]) / 2.0 + c2 * filt[i - 1] + c3 * filt[i - 2]
    return pd.Series(filt, index=data.index)


def _reversion_index(close: pd.Series, length: int):
    diff = close.diff()
    net_change = close - close.shift(length)
    sum_abs_change = diff.abs().rolling(length).sum()
    raw = net_change / sum_abs_change.replace(0, np.nan)
    raw = raw.fillna(0.0)

    smooth = _supersmoother(raw, length)
    trigger = _supersmoother(raw, max(2, length // 2))
    return smooth, trigger


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
    length: int = 10,
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

    smooth, trigger = _reversion_index(close, length)
    adx = _adx(high, low, close, adx_period)
    ranging = (adx < range_max_adx).fillna(False)

    valley = (trigger > smooth) & (trigger.shift(1) <= smooth.shift(1))
    peak = (trigger < smooth) & (trigger.shift(1) >= smooth.shift(1))
    valley = (valley & ranging).fillna(False)
    peak = peak.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(peak.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(valley.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    length: int = 10,
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
