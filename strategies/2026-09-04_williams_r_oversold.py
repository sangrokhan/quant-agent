"""Strategy: Williams %R deep-oversold mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-030):
Per QuantifiedStrategies.com's Williams %R article
(https://www.quantifiedstrategies.com/williams-r-strategy/): entry at
close when Williams %R < -90 (deep oversold, on a -100..0 scale) signals
a short-term mean-reversion opportunity; exit when today's close exceeds
yesterday's high OR Williams %R closes above -30. Source's own SPY
optimization (2-25 day lookback) found short lookbacks perform best (all
gave profit factor >= 1.9, best at a 2-day lookback), consistent with
other short-lookback oscillator mean-reversion findings already in this
repo (CCI 2026-09-04-024, RSI2 2026-09-03-005). First Williams %R
(bounded -100..0 oscillator, structurally similar to but distinct in
sign-convention/construction from both stochastic %K -- 2026-09-04-028,
0..100 scale, %K/%D crossover -- and CCI -- 2026-09-04-024, unbounded
mean-deviation scale) strategy tested in this repo.

Signal logic
------------
- Williams %R(williams_window) = -100 * (rolling_high(high, window) -
  close) / (rolling_high(high, window) - rolling_low(low, window)).
- Entry (long): close's Williams %R < oversold_threshold (source: -90).
- Exit: close > prior day's high (recovery breakout, source's rule) OR
  Williams %R > exit_threshold (source: -30).
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


def _williams_r(df: pd.DataFrame, williams_window: int) -> pd.Series:
    high_max = df["high"].rolling(williams_window).max()
    low_min = df["low"].rolling(williams_window).min()
    denom = (high_max - low_min).replace(0.0, pd.NA)
    return -100.0 * (high_max - df["close"]) / denom


def generate_signals(
    price_df: pd.DataFrame,
    williams_window: int = 2,
    oversold_threshold: float = -90.0,
    exit_threshold: float = -30.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    williams_r = _williams_r(df, williams_window)
    entry = (williams_r < oversold_threshold).fillna(False)
    prior_high = high.shift(1)
    exit_recover = (close > prior_high) | (williams_r > exit_threshold)
    exit_recover = exit_recover.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_recover.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
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
