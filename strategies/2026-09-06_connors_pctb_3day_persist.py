"""Strategy: Larry Connors' %b (Bollinger Percent-B) 3-day persistence
mean-reversion, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-092),
sourced from https://www.quantifiedstrategies.com/larry-connors-b-strategy/
("buying when the close is above the 200-day moving average, and %b is
below 0.2 for the last three consecutive days. The exit signal occurs when
%b closes above 0.8." -- QuantifiedStrategies used a 5-day Bollinger Band
lookback with 2 standard deviations since Connors' original book didn't
specify the BB parameters).

Distinct from this repo's already-tested plain %b mean-reversion
(2026-09-04-107, rejected: single-day %b<0 trigger, weak grid pass_fraction
6.25%, full-sample Sharpe 0.59, MDD 28.7%) via two mechanical differences:
  1. Requires %b < entry_threshold (0.2) to PERSIST for
     persistence_days (3) consecutive closes, not a single-day dip --
     screens for a sustained oversold condition rather than a one-bar
     spike, which the source's own results (75% win rate on an ETF
     portfolio) suggest reduces false starts from noisy single-day dips.
  2. Uses a much SHORTER Bollinger Band lookback (5 days vs the prior
     strategy's implied 20-day window) with 2 std devs -- a tighter,
     faster-reacting band that should generate more frequent but smaller
     mean-reversion setups.

Signal logic
------------
- %b = (close - lower_band) / (upper_band - lower_band), Bollinger Bands
  computed over bb_window days, bb_std standard deviations.
- Long entry: close > SMA(trend_window) (200d uptrend filter) AND
  %b < entry_threshold (0.2) on each of the last persistence_days (3)
  consecutive closes.
- Exit: %b closes above exit_threshold (0.8), or max_hold_days time-stop
  (repo standard safety valve; source strategy has no explicit stop-loss).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, position lagged by 1 day to avoid look-ahead bias)
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


def _percent_b(close: pd.Series, window: int, num_std: float) -> pd.Series:
    mid = close.rolling(window).mean()
    std = close.rolling(window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    pct_b = (close - lower) / (upper - lower)
    return pct_b


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 5,
    bb_std: float = 2.0,
    trend_window: int = 200,
    entry_threshold: float = 0.2,
    persistence_days: int = 3,
    exit_threshold: float = 0.8,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma_trend = close.rolling(trend_window).mean()
    pct_b = _percent_b(close, bb_window, bb_std)

    below_entry = pct_b < entry_threshold
    persisted = below_entry.rolling(persistence_days).sum() >= persistence_days
    uptrend = close > sma_trend

    entry_signal = (persisted & uptrend).fillna(False).values
    exit_signal = (pct_b > exit_threshold).fillna(False).values

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0

    for i in range(len(df.index)):
        if in_position:
            hold_count += 1
            if exit_signal[i] or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_signal[i]:
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
