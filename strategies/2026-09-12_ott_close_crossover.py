"""Strategy: Optimized Trend Tracker (OTT, Anil Ozeksi/KivancOzbilgic 2020)
close-crosses-OTT-line trend following.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
OTT is an adaptive trailing-stop trend line built from a Chande-Momentum-
-Oscillator-weighted Variable Index Dynamic Average (VIDYA/VAR), with a
percentage-band trailing-stop mechanism (a la SuperTrend/Chandelier Exit
but band-width scales with the VMA value rather than ATR). Per the
original creator's TradingView page (https://www.tradingview.com/script/
zVhoDQME/, KivancOzbilgic, visited via browser_exec/google.com fallback):
"We are under the effect of the uptrend in cases where the prices are
above OTT, under the influence of a downward trend, when prices are below
OTT... You can use OTT default alarms and Buy Sell signals like: 1- BUY
when Prices are above OTT, SELL when Prices are below OTT." Formula
details (VMA alpha weighted by |CMO|, trailing percent band `fark`) via
https://pineify.app/pine-script/indicators/optimized-trend-tracker.

Operationalized: VMA = CMO-weighted EMA of close (alpha scaled by
|CMO(cmo_period)|/100, so alpha increases with momentum strength); a
percentage band `fark = VMA * percent * 0.01` creates long/short trailing
stops that only move in the favorable direction (classic SuperTrend-style
ratchet); OTT line offsets the resulting trailing-stop midpoint by the
same percent band. Long entry when close crosses above OTT; exit (flat)
when close crosses below OTT, or a max_hold_days time-stop.

First OTT / VIDYA-trailing-stop strategy in this repo (distinct from
plain Chande Momentum Oscillator threshold-cross strategies already
tested, and distinct from SuperTrend/Chandelier Exit which use ATR for
band width rather than a percent-of-VMA band).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _cmo(close: pd.Series, cmo_period: int) -> pd.Series:
    """Chande Momentum Oscillator, range -100..100."""
    delta = close.diff()
    gains = delta.clip(lower=0.0)
    losses = (-delta).clip(lower=0.0)
    sum_gains = gains.rolling(cmo_period).sum()
    sum_losses = losses.rolling(cmo_period).sum()
    denom = (sum_gains + sum_losses).replace(0.0, np.nan)
    cmo = 100.0 * (sum_gains - sum_losses) / denom
    return cmo.fillna(0.0)


def _compute_ott(
    close: pd.Series, length: int, percent: float, cmo_period: int = 9
) -> pd.Series:
    """Vectorized-where-possible OTT line construction."""
    cmo = _cmo(close, cmo_period)
    base_alpha = 2.0 / (length + 1.0)
    alpha = (base_alpha * (cmo.abs() / 100.0)).clip(lower=0.0, upper=1.0)

    vals = close.values
    alpha_vals = alpha.values
    n = len(vals)
    vma = np.empty(n)
    vma[0] = vals[0]
    for i in range(1, n):
        a = alpha_vals[i] if not np.isnan(alpha_vals[i]) else base_alpha
        vma[i] = a * vals[i] + (1 - a) * vma[i - 1]

    fark = vma * percent * 0.01

    long_stop = vma - fark
    short_stop = vma + fark
    # trailing/ratcheting: long stop only moves up, short stop only moves down,
    # flip when price crosses the opposite stop (SuperTrend-style ratchet)
    mt = np.empty(n)
    direction = np.empty(n, dtype=int)
    mt[0] = long_stop[0]
    direction[0] = 1
    for i in range(1, n):
        if direction[i - 1] == 1:
            new_long_stop = max(long_stop[i], mt[i - 1]) if vma[i] > mt[i - 1] else long_stop[i]
            if vma[i] < new_long_stop:
                direction[i] = -1
                mt[i] = short_stop[i]
            else:
                direction[i] = 1
                mt[i] = new_long_stop
        else:
            new_short_stop = min(short_stop[i], mt[i - 1]) if vma[i] < mt[i - 1] else short_stop[i]
            if vma[i] > new_short_stop:
                direction[i] = 1
                mt[i] = long_stop[i]
            else:
                direction[i] = -1
                mt[i] = new_short_stop

    mt_series = pd.Series(mt, index=close.index)
    ott = np.where(vma > mt, mt_series * (200 + percent) / 200, mt_series * (200 - percent) / 200)
    return pd.Series(ott, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 2,
    percent: float = 1.4,
    cmo_period: int = 9,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ott = _compute_ott(close, length, percent, cmo_period)

    above = close > ott
    prev_above = above.shift(1)
    cross_up = above & ~prev_above.fillna(False)
    cross_down = ~above & prev_above.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]):
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
