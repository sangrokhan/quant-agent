"""Strategy: SuperTrend(ATR) trend follower gated by a low/mid volatility regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-010):
Direct fix attempt for this cron trigger's near-miss SuperTrend result
(id=2026-09-09-005): QQQ passed 4/5 validators but missed max_drawdown by
only 0.6 percentage points (0.256 vs 0.25 threshold); SPY passed 4/5 but
missed Sharpe by 0.097 (0.903 vs 1.0). That grid also showed the strategy's
edge concentrated entirely in low/mid volatility regimes (18/36 low, 9/36
mid, 0/36 high pass) and 0/54 on crypto. This iteration adds an explicit
volatility-regime gate (20-day realized vol vs its trailing 1-year median,
same construction pattern already validated as an accepted-strategy
mechanism in this repo, e.g. 2026-09-03-001's BB mean-reversion
low-vol-regime filter) to exclude new entries during high-vol regimes --
directly targeting the failure mode the grid already diagnosed, rather than
guessing at a new indicator combination.

Signal logic
------------
- SuperTrend(atr_window, mult): identical ATR-based dynamic band/line
  construction as the base strategy (2026-09-09_supertrend_atr_trend_follow.py).
- Volatility regime: 20-day realized vol (annualized std of daily log
  returns) compared to its own trailing 252-day median; "low/mid" regime =
  current vol <= vol_regime_ratio x that median.
- Entry (long): close crosses above the SuperTrend line (bullish flip) AND
  we are in the low/mid vol regime.
- Exit: close crosses below the SuperTrend line (bearish flip), OR the
  vol regime flips to high-vol (risk-off exit, closing the position even
  mid-trend), OR max_hold_days elapses (new safety backstop the original
  strategy lacked, since unfiltered SuperTrend has no max hold).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def _supertrend(df: pd.DataFrame, atr_window: int, mult: float) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    hl2 = (high + low) / 2.0
    atr = _atr(df, atr_window)

    basic_upper = hl2 + mult * atr
    basic_lower = hl2 - mult * atr

    n = len(df)
    final_upper = np.full(n, np.nan)
    final_lower = np.full(n, np.nan)
    supertrend = np.full(n, np.nan)
    direction = np.ones(n, dtype=int)

    bu = basic_upper.values
    bl = basic_lower.values
    c = close.values

    for i in range(n):
        if np.isnan(bu[i]) or np.isnan(bl[i]):
            continue
        if i == 0 or np.isnan(final_upper[i - 1]):
            final_upper[i] = bu[i]
            final_lower[i] = bl[i]
            direction[i] = 1 if c[i] >= final_lower[i] else -1
            supertrend[i] = final_lower[i] if direction[i] == 1 else final_upper[i]
            continue

        final_upper[i] = bu[i] if (bu[i] < final_upper[i - 1] or c[i - 1] > final_upper[i - 1]) else final_upper[i - 1]
        final_lower[i] = bl[i] if (bl[i] > final_lower[i - 1] or c[i - 1] < final_lower[i - 1]) else final_lower[i - 1]

        prev_dir = direction[i - 1]
        if prev_dir == 1:
            direction[i] = -1 if c[i] < final_lower[i] else 1
        else:
            direction[i] = 1 if c[i] > final_upper[i] else -1

        supertrend[i] = final_lower[i] if direction[i] == 1 else final_upper[i]

    return pd.Series(supertrend, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    atr_window: int = 14,
    mult: float = 4.0,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    st_line = _supertrend(df, atr_window, mult)

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median_1y = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_mid_vol_regime = realized_vol <= (vol_median_1y * vol_regime_ratio)

    bullish_trend = close > st_line
    entry_signal = bullish_trend & bullish_trend.shift(1).fillna(False).eq(False) & low_mid_vol_regime.fillna(False)

    close_vals = close.values
    entry_sig_vals = entry_signal.fillna(False).values
    bearish_flip_vals = (~bullish_trend).fillna(True).values
    high_vol_vals = (~low_mid_vol_regime).fillna(True).values

    n = len(close_vals)
    position_vals = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(bearish_flip_vals[i]) or bool(high_vol_vals[i]) or held >= max_hold_days:
                in_position = False
                position_vals[i] = 0
                continue
            position_vals[i] = 1
        else:
            if bool(entry_sig_vals[i]):
                in_position = True
                entry_idx = i
                position_vals[i] = 1
            else:
                position_vals[i] = 0

    return pd.Series(position_vals, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
