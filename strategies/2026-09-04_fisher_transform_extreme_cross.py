"""Strategy: Fisher Transform extreme-threshold-gated crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-051):
Per a Google AI-overview synthesis (onetradejournal.com et al.): John
Ehlers' Fisher Transform normalizes price into a bounded (-1,+1) range
then applies the inverse hyperbolic tangent transform to sharpen turning
points into distinct extreme peaks (approximately Gaussian-distributed,
unlike raw price which tends to be non-Gaussian). Long entry: wait for
the Fisher line to drop below an extreme negative threshold (-1.5), then
enter when the Fisher line crosses above its own 1-bar-lagged trigger
line. Exit: Fisher line crosses back below the trigger line. The
source's own backtest insight: focusing exclusively on extreme-threshold
crossovers (ignoring near-zero-line noise) improves win rate/profit
factor vs an unfiltered every-crossover approach.

Fisher Transform formula (standard, Ehlers):
    value = 2 * ((close - low_n) / (high_n - low_n) - 0.5)   # normalized to (-1,1)
    value = clamp(0.999 * smoothed_value, -0.999, 0.999)      # avoid ln(0)/asymptote
    fisher_t = 0.5 * ln((1+value)/(1-value)) + 0.5 * fisher_{t-1}
    trigger = fisher.shift(1)

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _fisher_transform(close: pd.Series, window: int = 10) -> pd.Series:
    low_n = close.rolling(window).min()
    high_n = close.rolling(window).max()
    rng = (high_n - low_n).replace(0, pd.NA)
    raw = 2 * ((close - low_n) / rng - 0.5)
    raw = raw.fillna(0.0)

    # Smooth the normalized value slightly (standard Ehlers construction
    # uses a light EMA-like recursive smooth before the log transform).
    smoothed = pd.Series(index=close.index, dtype=float)
    prev_smoothed = 0.0
    prev_fisher = 0.0
    fisher = pd.Series(index=close.index, dtype=float)
    for i, idx in enumerate(close.index):
        v = raw.loc[idx]
        s = 0.33 * v + 0.67 * prev_smoothed
        s = max(min(s, 0.999), -0.999)
        smoothed.loc[idx] = s
        f = 0.5 * math.log((1 + s) / (1 - s)) + 0.5 * prev_fisher
        fisher.loc[idx] = f
        prev_smoothed = s
        prev_fisher = f
    return fisher


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 10,
    extreme_threshold: float = 1.5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fisher = _fisher_transform(close, window=window)
    trigger = fisher.shift(1)

    was_extreme_low = fisher.shift(1) < -extreme_threshold
    # Track "has been extreme in the recent past" with a short lookback
    # window (source: "wait for the Fisher line to drop below the
    # threshold, THEN enter on the crossover" -- not necessarily the very
    # next bar).
    recently_extreme = was_extreme_low.rolling(5, min_periods=1).max().astype(bool)

    bullish_cross = (fisher > trigger) & (fisher.shift(1) <= trigger.shift(1))
    bearish_cross = (fisher < trigger) & (fisher.shift(1) >= trigger.shift(1))

    entry = bullish_cross.fillna(False) & recently_extreme.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(bearish_cross.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
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
