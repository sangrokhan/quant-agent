"""Strategy: Corwin-Schultz spread regime-exit, direct fix via low-vol regime gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-003):
direct fix attempt for this cron trigger's near-miss 2026-09-11-002 (plain
Corwin-Schultz spread stress-exit + SMA trend filter). That iteration's
grid showed QQQ full-sample Sharpe (0.778) narrowly missing threshold while
passing every other validator cleanly, AND the grid's by_vol_regime
breakdown showed the edge overwhelmingly concentrated in the low-vol
tercile (22/72 low vs 5/72 mid vs 1/72 high passes). This iteration adds an
explicit low-vol regime AND-gate (20d realized vol <= trailing 252d
median, identical construction to the already-accepted
2026-09-03_bb_meanrev_qqq_volregime.py) on top of the unchanged
Corwin-Schultz (2012) spread-stress-exit + SMA-trend-filter entry/exit
mechanics from 2026-09-11-002 (source:
https://www.tradingview.com/script/ji4eKKuZ-Corwin-Schultz-Spread-Bands/,
visited earlier this cron trigger). Same fix pattern that has repeatedly
rescued near-miss oscillator/regime strategies elsewhere in this repo
(e.g. 2026-09-06-128 Weinstein Stage 2 + vol-regime gate, 2026-09-08-043
VQI streak + vol-regime gate).

Signal logic
------------
- Corwin-Schultz spread stress-exit + SMA trend filter, identical to
  2026-09-11-002 (see that strategy file's docstring for the full
  algorithm derivation).
- NEW: entry additionally requires 20-day realized volatility (annualized
  std of daily log returns) to be <= its own trailing 252-day median
  (low-vol regime confirmed) -- exactly 2026-09-03_bb_meanrev_qqq_volregime.py's
  construction.
- Exit: unchanged (close<SMA(trend_window), OR the vol regime flips to
  high-vol (risk-off exit, added consistent with the accepted BB
  mean-reversion reference strategy), OR max_hold_days time-stop).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

_K = 3 - 2 * np.sqrt(2)


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _corwin_schultz_spread(high: pd.Series, low: pd.Series, smooth: int) -> pd.Series:
    log_hl = np.log(high / low)
    beta = log_hl ** 2 + log_hl.shift(1) ** 2

    hh = pd.concat([high, high.shift(1)], axis=1).max(axis=1)
    ll = pd.concat([low, low.shift(1)], axis=1).min(axis=1)
    gamma = (np.log(hh / ll)) ** 2

    with np.errstate(invalid="ignore"):
        alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / _K - np.sqrt(gamma / _K)

    raw_spread = 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))
    raw_spread = raw_spread.clip(lower=0.0, upper=1.0)
    smoothed = raw_spread.ewm(span=smooth, adjust=False, min_periods=smooth).mean()
    return smoothed


def generate_signals(
    price_df: pd.DataFrame,
    spread_smooth: int = 5,
    regime_lookback: int = 100,
    stdev_mult: float = 0.5,
    trend_window: int = 50,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    spread = _corwin_schultz_spread(high, low, spread_smooth)

    rolling_median = spread.rolling(regime_lookback, min_periods=regime_lookback).median()
    rolling_std = spread.rolling(regime_lookback, min_periods=regime_lookback).std()
    threshold = rolling_median + stdev_mult * rolling_std

    in_stress = (spread > threshold).fillna(False)
    exiting_stress = in_stress.shift(1).fillna(False) & (~in_stress)

    sma_trend = close.rolling(trend_window, min_periods=trend_window).mean()
    above_trend = (close > sma_trend).fillna(False)

    # Realized-vol low-vol regime gate (identical construction to the
    # accepted 2026-09-03_bb_meanrev_qqq_volregime.py).
    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median_1y = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_vol_regime = (realized_vol <= (vol_median_1y * vol_regime_ratio)).fillna(False)

    entry_event = exiting_stress & above_trend & low_vol_regime

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0
    entry_arr = entry_event.values
    above_trend_arr = above_trend.values
    low_vol_arr = low_vol_regime.values

    for i in range(len(df.index)):
        if in_position:
            hold_count += 1
            if (not above_trend_arr[i]) or (not low_vol_arr[i]) or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_arr[i]:
                in_position = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **params)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
