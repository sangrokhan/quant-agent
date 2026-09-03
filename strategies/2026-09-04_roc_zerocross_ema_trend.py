"""Strategy: ROC(12) zero-cross momentum, EMA(50) trend-filtered.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-039):
Per Google AI-overview + Quantified Strategies' Rate of Change article:
ROC(12) (12-period percentage rate of change) crossing above zero,
combined with a shorter-horizon trend filter (close > EMA(50)), signals a
long entry that should reduce false signals in choppy/ranging markets
versus a raw ROC-only or EMA-only rule. Exit when either condition breaks
(ROC crosses back below zero, or price falls below the EMA(50)). Distinct
from the prior momentum+trend-filter combination already tested in this
repo (2026-09-03-004, which used a raw trailing-return threshold + 200d
SMA -- a longer, coarser pairing) by using a bounded percentage-ROC
oscillator's own zero-cross plus a shorter EMA(50).

Signal logic
------------
- ROC(roc_window) = (close / close.shift(roc_window) - 1) * 100.
- Entry (long): ROC > 0 AND close > EMA(ema_window).
- Exit: ROC <= 0 OR close <= EMA(ema_window).
- Flat otherwise; long-only, no shorting (source's ATR-stop/position-sizing
  overlay not implemented -- out of scope for the core signal test, per
  this repo's convention of testing the raw indicator logic first).

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


def generate_signals(
    price_df: pd.DataFrame,
    roc_window: int = 12,
    ema_window: int = 50,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    roc = (close / close.shift(roc_window) - 1.0) * 100.0
    ema = close.ewm(span=ema_window, adjust=False).mean()

    condition = (roc > 0) & (close > ema)
    position = condition.fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
