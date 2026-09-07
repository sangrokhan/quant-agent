"""Strategy: CCI Range Re-Entry (oversold recovery cross), range-bound gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-088),
sourced from https://fxglory.com/learn/forex-strategies/cci-forex-strategy
("CCI Forex Strategy: Test Re-Entry, Zero-Line, Divergence, and MA
Setups"). Concrete rule quoted from the source's "CCI Range Re-Entry
Strategy" section:

    "Context: Higher timeframe is range-like or sideways."
    "Long idea: CCI moves below -100, then crosses back above -100 near
    support or range low."
    "Skip rule: Skip when price is trending strongly or the range is too
    narrow after spread."

I.e. distinct from every other CCI strategy already tested in this repo
(oversold-THRESHOLD-cross mean-reversion at 2026-09-04-024 which enters ON
the breach below the threshold; trend-continuation breakout above +100 at
2026-09-04-072; Woodie's Zero-Line-Reject and trend-line-break variants) --
here the entry trigger is the RECOVERY cross back above -100 AFTER having
gone below it (a re-entry into the "normal" zone from oversold, not the
initial breach), and it is explicitly gated to range-bound/non-trending
conditions per the source's own context requirement (operationalized here
via ADX(14) below a threshold, the standard non-trending-regime proxy
already used elsewhere in this repo, e.g. VHF-gated Donchian breakout).

Exit: CCI reaching the source's own zero-line reference point (mean
reversion complete) or a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _cci(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 20) -> pd.Series:
    tp = (high + low + close) / 3.0
    sma_tp = tp.rolling(window).mean()
    import numpy as np

    mean_dev = tp.rolling(window).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    cci = (tp - sma_tp) / (0.015 * mean_dev.replace(0.0, pd.NA))
    return cci


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = ((up_move > down_move) & (up_move > 0)) * up_move
    minus_dm = ((down_move > up_move) & (down_move > 0)) * down_move

    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, pd.NA)
    adx = dx.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    cci_window: int = 20,
    oversold_threshold: float = -100.0,
    exit_cci_level: float = 0.0,
    adx_window: int = 14,
    adx_range_ceiling: float = 20.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    cci = _cci(high, low, close, cci_window)
    adx = _adx(high, low, close, adx_window)
    range_bound = adx < adx_range_ceiling

    cci_prev = cci.shift(1)
    reentry_cross = (cci_prev < oversold_threshold) & (cci >= oversold_threshold)
    entry = reentry_cross.fillna(False) & range_bound.fillna(False)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = 0
    for i in range(n):
        if in_pos:
            held = i - entry_idx
            exit_signal = (not pd.isna(cci.iloc[i])) and cci.iloc[i] >= exit_cci_level
            if exit_signal or held >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_pos = True
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
