"""Strategy: Stochastic Oscillator oversold/overbought zone-gated crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-028):
Per QuantifiedStrategies.com's stochastic indicator article
(https://www.quantifiedstrategies.com/stochastic-indicator-strategy/):
a short-term mean-reversion edge exists when %K crosses above %D WHILE
BELOW an oversold threshold (source uses 20), long-only. Their own SPY
backtest (1993-present, 556 trades) reports profit factor 2.2, MDD 19.8%,
avg gain 0.57%/trade. The source explicitly states a PURE %K/%D crossover
(without the zone gate) tested worse in their own research -- this
strategy implements the zone-gated version as instructed. Exit when %K
crosses back above the oversold threshold (source recommends a low
threshold + minimal smoothing for responsiveness) or after
max_hold_days. First stochastic-oscillator (bounded 0-100
range-position indicator, distinct calculation from RSI's average
gain/loss ratio) strategy tested in this repo.

Signal logic
------------
- %K = 100 * (close - rolling_low(low, k_window)) / (rolling_high(high,
  k_window) - rolling_low(low, k_window)).
- %D = SMA(%K, d_window) (signal line).
- Entry (long): %K crosses from <= %D to > %D, AND %K < oversold_threshold
  at the crossover bar (oversold zone gate, per source's finding that the
  ungated crossover underperforms).
- Exit: %K crosses back above oversold_threshold (mean-reversion target
  reached), OR after max_hold_days bars.
- Flat otherwise; long-only, no shorting.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _stochastic(df: pd.DataFrame, k_window: int, d_window: int) -> tuple[pd.Series, pd.Series]:
    low_min = df["low"].rolling(k_window).min()
    high_max = df["high"].rolling(k_window).max()
    denom = (high_max - low_min).replace(0.0, pd.NA)
    pct_k = 100.0 * (df["close"] - low_min) / denom
    pct_d = pct_k.rolling(d_window).mean()
    return pct_k, pct_d


def generate_signals(
    price_df: pd.DataFrame,
    k_window: int = 14,
    d_window: int = 3,
    oversold_threshold: float = 20.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    pct_k, pct_d = _stochastic(df, k_window, d_window)
    k_above_d = pct_k > pct_d
    cross_up = k_above_d & (~k_above_d.shift(1).fillna(False))
    entry = cross_up & (pct_k < oversold_threshold)
    entry = entry.fillna(False)

    exit_recover = pct_k >= oversold_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_recover.iloc[i]) or held >= max_hold_days:
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
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
