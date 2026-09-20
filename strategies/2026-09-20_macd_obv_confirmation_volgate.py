"""Strategy: MACD+OBV Confirmation gated by Low-Volatility Regime.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-136):
Direct rescue attempt of this same cron trigger's near-miss 2026-09-20-135
(Price MACD crossover gated by OBV-MACD confirmation): that strategy's own
grid test showed a striking regime split -- pass_fraction 0.528 in
low-volatility bars vs 0.083 in mid-vol and 0.167 in high-vol -- while its
full-sample (all-regime) Sharpe fell just short of the 1.0 acceptance
threshold on both QQQ (0.790) and SPY (0.783), with every OTHER validator
(MDD, tx-cost, walk-forward, and especially parameter sensitivity, the
most stable of any strategy tested this cron trigger) passing comfortably.
This iteration adds an explicit realized-volatility regime gate (20-day
realized vol <= vol_regime_ratio x trailing 252-day median, the same
mechanic as this repo's own established
2026-09-03_bb_meanrev_qqq_volregime.py pattern) on TOP of the unchanged
MACD+OBV entry/exit logic, to test whether restricting trades to the
regime where the signal actually works pushes the full-sample Sharpe over
threshold, following this repo's successful precedent of rescuing
regime-dependent near-misses this way.

Signal logic
------------
- Identical price-MACD / OBV-MACD confirmation entry and exit as
  2026-09-20-135 (see that file's docstring for the full construction).
- ADDED: entry is only taken when 20-day realized volatility (annualized
  std of daily log returns) is <= vol_regime_ratio times its own trailing
  252-day median (low-vol regime gate). Existing positions are NOT force-
  closed on a regime flip (unlike the BB mean-reversion strategy) -- this
  isolates the effect of gating NEW entries only, matching this repo's
  simplest rescue-pattern variant.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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


def _macd(series: pd.Series, fast: int, slow: int, signal_len: int):
    macd_line = series.ewm(span=fast, adjust=False).mean() - series.ewm(span=slow, adjust=False).mean()
    signal_line = macd_line.ewm(span=signal_len, adjust=False).mean()
    return macd_line, signal_line


def generate_signals(
    price_df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal_len: int = 9,
    max_hold_days: int = 40,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    price_macd, price_signal = _macd(close, fast, slow, signal_len)

    direction = np.sign(close.diff().fillna(0.0))
    signed_volume = direction * volume
    obv = signed_volume.cumsum()

    obv_macd, obv_signal = _macd(obv, fast, slow, signal_len)

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median_1y = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_vol_regime = (realized_vol <= (vol_median_1y * vol_regime_ratio)).fillna(False)

    price_cross_up = (price_macd > price_signal) & (price_macd.shift(1) <= price_signal.shift(1))
    price_cross_down = (price_macd < price_signal) & (price_macd.shift(1) >= price_signal.shift(1))
    obv_confirms = obv_macd > obv_signal

    entry = (price_cross_up & obv_confirms & low_vol_regime).fillna(False)
    exit_signal = price_cross_down.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(len(close)):
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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
