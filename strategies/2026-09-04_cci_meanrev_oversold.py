"""Strategy: CCI (Commodity Channel Index) oversold mean-reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-024):
Per a QuantifiedStrategies.com backtest article, a short-lookback CCI
(9-day, best suited to daily stock/ETF data per the source) that dips below
an oversold threshold (source uses -90) signals an extreme short-term
mean-reversion opportunity: long when CCI crosses below the oversold
threshold, exit when price exceeds the pre-entry rolling high (a "recovery
above resistance" exit rather than a fixed-bar hold or return-to-mean-band
exit). Source's own SPY backtest reported profit factor ~1.8, max drawdown
~23%. This is the first CCI-based strategy tested in this repo -- distinct
oscillator construction from RSI (uses raw deviation from a mean-deviation
band scaled by a constant, unbounded, rather than a bounded 0-100 RSI
scale) and from Bollinger/Keltner (price bands, not an oscillator).

Signal logic
------------
- CCI(cci_window) = (typical_price - SMA(typical_price, cci_window)) /
  (0.015 * mean_abs_deviation(typical_price, cci_window)).
  typical_price = (high + low + close) / 3.
- Entry (long): CCI crosses from >= oversold_threshold to < oversold_threshold
  (fresh cross into oversold territory, not just "is below").
- Exit: close exceeds the highest high observed in the exit_lookback bars
  immediately preceding entry (source's "price exceeds prior high" rule),
  OR after max_hold_days bars (avoid indefinite holds during prolonged
  drawdowns where price never regains the pre-entry high).
- Flat otherwise (long-only, no shorting).

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


def _cci(df: pd.DataFrame, cci_window: int) -> pd.Series:
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    sma_tp = typical_price.rolling(cci_window).mean()
    import numpy as np

    mad = typical_price.rolling(cci_window).apply(
        lambda x: np.abs(x - x.mean()).mean(), raw=True
    )
    cci = (typical_price - sma_tp) / (0.015 * mad.replace(0.0, pd.NA))
    return cci


def generate_signals(
    price_df: pd.DataFrame,
    cci_window: int = 9,
    oversold_threshold: float = -90.0,
    exit_lookback: int = 20,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    cci = _cci(df, cci_window)
    prev_cci = cci.shift(1)
    entry = (prev_cci >= oversold_threshold) & (cci < oversold_threshold)
    entry = entry.fillna(False)

    # Rolling high over the exit_lookback bars strictly before "today"
    # (pre-entry resistance level the source's exit rule references).
    prior_high = df["high"].rolling(exit_lookback).max().shift(1)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_target_high = None

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_recover = bool(close.iloc[i] > entry_target_high) if entry_target_high == entry_target_high else False
            if exit_recover or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                entry_target_high = None
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                entry_target_high = prior_high.iloc[i]
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
