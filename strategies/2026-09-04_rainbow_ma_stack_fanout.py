"""Strategy: Rainbow Moving Average stack + fan-out trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-135):
Per quantifiedstrategies.com and forexmt4indicators.com, the "Rainbow"
moving average is a cascade of N moving averages, where layer 1 is an
SMA(period) of price and each subsequent layer k is an SMA(period) of
layer k-1 (progressive smoothing). The sources' own trend-strength
mechanic: when the layers are perfectly "stacked" in trend order (each
faster layer above the next slower layer for an uptrend) AND the fan-out
(spread between the fastest and slowest layer) is widening, that signals
a strong, accelerating trend; layers converging/tangled signals a weak or
absent trend. This is a testable simplification of the sources' full
3-indicator combo strategy (Rainbow MMA + HMA-dot pullback trigger +
fractal stop) -- distinct from this repo's existing HMA-crossover and
Fractal-breakout strategies (already tested separately), isolating just
the Rainbow stack/fan-out mechanic itself as an independent signal.

Signal logic
------------
- layers[0] = SMA(close, period)
- layers[k] = SMA(layers[k-1], period) for k = 1..n_layers-1
- stacked_bull = layers[0] > layers[1] > ... > layers[n_layers-1] (perfect
  bullish alignment, fastest on top)
- fan_spread = (layers[0] - layers[-1]) / close  (normalized fan-out width)
- Entry (long): stacked_bull is newly true (wasn't true yesterday) AND
  fan_spread > fan_threshold (require a real trend, not just barely stacked)
- Exit: stacked_bull becomes false (alignment breaks), OR max_hold_days
  time-stop.
- Long-only, flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rainbow_layers(close: pd.Series, period: int, n_layers: int) -> list[pd.Series]:
    layers = []
    prev = close
    for _ in range(n_layers):
        layer = prev.rolling(period).mean()
        layers.append(layer)
        prev = layer
    return layers


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 5,
    n_layers: int = 6,
    fan_threshold: float = 0.01,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(df)

    layers = _rainbow_layers(close, period, n_layers)

    stacked_bull = pd.Series(True, index=df.index)
    for k in range(n_layers - 1):
        stacked_bull &= layers[k] > layers[k + 1]

    fan_spread = (layers[0] - layers[-1]) / close

    stacked_bull_prev = stacked_bull.shift(1).fillna(False)
    entry_trigger = stacked_bull & (~stacked_bull_prev) & (fan_spread > fan_threshold)
    exit_trigger = ~stacked_bull

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            et = bool(exit_trigger.iloc[i]) if pd.notna(exit_trigger.iloc[i]) else True
            if et or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            entered = bool(entry_trigger.iloc[i]) if pd.notna(entry_trigger.iloc[i]) else False
            if entered:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    period: int = 5,
    n_layers: int = 6,
    fan_threshold: float = 0.01,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df, period=period, n_layers=n_layers, fan_threshold=fan_threshold,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
