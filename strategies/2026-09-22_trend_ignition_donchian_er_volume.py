"""Strategy: Trend Ignition -- Donchian breakout + efficiency-ratio quality filter + volume surge.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-105):
Per ChartCrypto.app's "Trend Ignition" backtesting strategy page
(https://chartcrypto.app/backtesting/trend-ignition), a genuine breakout
needs THREE conditions true on the same bar:
  1. close > prior 20-bar high (Donchian breakout)
  2. 20-bar Kaufman Efficiency Ratio (ER = |close - close[t-20]| /
     sum(|close.diff()|, 20)) > 0.3 (net move is a real trend, not chop)
  3. 5-bar average volume >= 1.2x the 20-bar average volume (real
     participation, not a thin-volume fakeout)
"A breakout that fails any check is treated as noise and skipped."

Exit: close crosses back below the 20-bar SMA, OR closes below the prior
10-bar low, backstopped by a max_hold_days time-stop.

Distinct from this repo's existing Kaufman Efficiency Ratio entries: all
11+ prior ER entries use ER as either (a) a KAMA adaptive-smoothing input,
(b) a standalone ER-vs-threshold trend/chop regime gate on a WMA/EMA
crossover system, or (c) a continuous sizing dial -- none combine ER with a
Donchian-channel breakout AND an independent relative-volume-surge filter
as a triple-AND-gated entry condition. This is the first
breakout-quality-filter construction of this specific shape in this repo.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _compute_er(close: pd.Series, window: int) -> pd.Series:
    net_change = (close - close.shift(window)).abs()
    path_length = close.diff().abs().rolling(window).sum()
    safe_path = path_length.where(path_length != 0, 1e-12)
    return (net_change / safe_path).astype(float)


def generate_signals(
    price_df: pd.DataFrame,
    donchian_window: int = 20,
    er_window: int = 20,
    er_threshold: float = 0.3,
    fast_vol_window: int = 5,
    slow_vol_window: int = 20,
    vol_ratio_threshold: float = 1.2,
    exit_sma_window: int = 20,
    exit_lookback: int = 10,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    donchian_high = close.rolling(donchian_window).max().shift(1)
    breakout = close > donchian_high

    er = _compute_er(close, er_window)
    er_ok = er > er_threshold

    fast_vol = volume.rolling(fast_vol_window).mean()
    slow_vol = volume.rolling(slow_vol_window).mean()
    safe_slow_vol = slow_vol.where(slow_vol != 0, 1e-12)
    vol_ratio = fast_vol / safe_slow_vol
    vol_ok = vol_ratio >= vol_ratio_threshold

    entry_trigger = breakout & er_ok & vol_ok

    exit_sma = close.rolling(exit_sma_window).mean()
    exit_prior_low = close.rolling(exit_lookback).min().shift(1)
    exit_trigger = (close < exit_sma) | (close < exit_prior_low)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_trigger.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
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
