"""Strategy: Balance of Power (BOP) smoothed threshold crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-071):
Per IBKR Glossary + TradingView community strategy synthesis: BOP
(Balance of Power) = (Close - Open) / (High - Low), a bounded -1..1
intrabar-position measure of buyer/seller dominance, optionally smoothed
by a moving average. Distinct calculation basis from RVI (2026-09-04-061,
4-bar triangular-weighted close-vs-open/high-low ratio) already tested.
Long entry when smoothed BOP crosses above a high threshold (rescaled to
0.15-0.3 for a 14-day-smoothed BOP based on observed data distribution,
since the naively-cited 0.8 TradingView threshold never triggers on
daily-smoothed BOP -- it was likely intended for unsmoothed intrabar
BOP), signaling strong buyer dominance; exit when smoothed BOP crosses
back below zero (common BOP exit convention).

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
    bop_window: int = 14,
    entry_threshold: float = 0.2,
    exit_threshold: float = 0.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, open_, high, low = df["close"], df["open"], df["high"], df["low"]

    range_ = (high - low).replace(0, 1e-12)
    raw_bop = (close - open_) / range_
    smoothed_bop = raw_bop.rolling(bop_window).mean()

    entry_signal = (smoothed_bop > entry_threshold) & (smoothed_bop.shift(1) <= entry_threshold)
    exit_signal = smoothed_bop < exit_threshold

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
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
