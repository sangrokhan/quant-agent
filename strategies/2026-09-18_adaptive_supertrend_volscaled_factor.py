"""Strategy: Adaptive SuperTrend (volatility-scaled ATR factor), stop-and-
reverse trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-010):
Per ForexCracked's "Adaptive Supertrend" article
(https://www.forexcracked.com/forex-indicator/adaptive-supertrend-indicator-tradingview/,
read via browser_exec after web_search DDGS/Yahoo backend errored with
TLS RequestError on every query attempted this iteration): the classic
SuperTrend (Olivier Seban) uses a FIXED ATR multiplier factor, which
whipsaws in ranging markets (factor too small) or lags in fast trends
(factor too large). The disclosed fix: rank the current ATR against its
own recent rolling range to get a 0-100 "volatility score" (percentile
rank), then linearly map that score onto a factor between a Min and Max
bound -- low volatility score -> small factor (tighter trail, earlier
entries); high volatility score -> large factor (wider trail, fewer false
flips during volatility spikes). This iteration builds the standard
SuperTrend construction (ATR bands around HL2 midpoint, stop-and-reverse
state machine) but with this adaptive per-bar factor replacing the fixed
multiplier already tested in this repo's plain SuperTrend
(2026-09-04-053, accepted QQQ/SPY, rejected crypto). First
volatility-adaptive-factor SuperTrend variant in this repo -- distinct
from every other SuperTrend combination already tested (plain, Choppiness
Index gate, Chandelier dual-confirm, Pivot-Point-anchored center line),
none of which vary the ATR multiplier itself based on volatility regime.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position series).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _adaptive_factor(
    atr: pd.Series, vol_lookback: int, factor_min: float, factor_max: float
) -> pd.Series:
    """Percentile-rank the current ATR against its own trailing
    `vol_lookback`-bar window (0-100 volatility score), linearly map to
    [factor_min, factor_max].
    """
    vol_score = atr.rolling(vol_lookback).rank(pct=True) * 100.0
    factor = factor_min + (vol_score / 100.0) * (factor_max - factor_min)
    return factor


def generate_signals(
    price_df: pd.DataFrame,
    atr_period: int = 10,
    vol_lookback: int = 100,
    factor_min: float = 1.5,
    factor_max: float = 4.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series (stop-and-reverse
    SuperTrend state machine with a volatility-adaptive ATR factor)."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr = _true_range(df)
    atr = tr.ewm(span=atr_period, adjust=False, min_periods=atr_period).mean()
    factor = _adaptive_factor(atr, vol_lookback, factor_min, factor_max)

    hl2 = (high + low) / 2.0
    basic_upper = hl2 + factor * atr
    basic_lower = hl2 - factor * atr

    n = len(close)
    final_upper = pd.Series(0.0, index=close.index)
    final_lower = pd.Series(0.0, index=close.index)
    trend = pd.Series(1, index=close.index, dtype=int)  # 1=up, -1=down

    close_vals = close.to_numpy()
    bu = basic_upper.to_numpy()
    bl = basic_lower.to_numpy()
    fu = final_upper.to_numpy().copy()
    fl = final_lower.to_numpy().copy()
    tr_state = trend.to_numpy().copy()

    for i in range(n):
        if pd.isna(bu[i]) or pd.isna(bl[i]):
            fu[i] = bu[i] if not pd.isna(bu[i]) else float("nan")
            fl[i] = bl[i] if not pd.isna(bl[i]) else float("nan")
            tr_state[i] = tr_state[i - 1] if i > 0 else 1
            continue

        if i == 0 or pd.isna(fu[i - 1]) or pd.isna(fl[i - 1]):
            # first valid bar after the initial NaN warm-up window
            fu[i] = bu[i]
            fl[i] = bl[i]
            tr_state[i] = 1
            continue

        fu[i] = bu[i] if (bu[i] < fu[i - 1] or close_vals[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = bl[i] if (bl[i] > fl[i - 1] or close_vals[i - 1] < fl[i - 1]) else fl[i - 1]

        if tr_state[i - 1] == 1:
            tr_state[i] = -1 if close_vals[i] < fl[i] else 1
        else:
            tr_state[i] = 1 if close_vals[i] > fu[i] else -1

    position = pd.Series((tr_state == 1).astype(int), index=close.index)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
