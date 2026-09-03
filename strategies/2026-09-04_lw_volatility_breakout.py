"""Strategy: Larry Williams-style volatility breakout (daily-bar adaptation).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-069):
Per DisciplineAI's Larry Williams Volatility Breakout article: take the
prior day's range (Range = PriorHigh - PriorLow), multiply by a constant
k (typical daily-swing value 0.25-0.40), and add to the prior day's high
to get a long entry trigger. Original system uses an intraday stop-buy
order; since this repo's loaders provide only daily OHLCV, adapted here
as: long entry when today's CLOSE exceeds (prior-day high + k * prior-day
range), signaling a strong breakout day; exit after a fixed hold period
(max_hold_days) or when close falls back below the prior-day low.
Distinct from Donchian breakout (2026-09-03-008/-054, N-day rolling
extreme) since this uses only the single PRIOR day's range scaled by k.

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
    k: float = 0.3,
    max_hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, high, low = df["close"], df["high"], df["low"]

    prior_high = high.shift(1)
    prior_low = low.shift(1)
    prior_range = prior_high - prior_low
    trigger = prior_high + k * prior_range

    entry_signal = close > trigger

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_counter = 0
    for i in range(len(df)):
        if in_position:
            hold_counter += 1
            exit_now = (hold_counter >= max_hold_days) or (
                not pd.isna(prior_low.iloc[i]) and close.iloc[i] < prior_low.iloc[i]
            )
            if exit_now:
                in_position = False
                hold_counter = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_position = True
                hold_counter = 0
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
