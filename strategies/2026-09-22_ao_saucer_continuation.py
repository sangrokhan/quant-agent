"""Strategy: Awesome Oscillator (AO) Saucer momentum-continuation pattern.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-006):
Per TradingStrategyGuides' disclosed rule
(https://tradingstrategyguides.com/bill-williams-awesome-oscillator-strategy/):
AO = SMA(median_price, 5) - SMA(median_price, 34), where median_price =
(High+Low)/2. A bullish "Saucer" signals momentum continuation within an
existing uptrend: (1) AO histogram is above zero, (2) two consecutive red
(declining) bars where the 2nd bar is lower than the 1st, (3) a 3rd bar is
green (AO ticks up) and higher than the 2nd bar. This is a 3-bar
continuation trigger, distinct from AO's more commonly-tested zero-line
crossover and Twin Peaks divergence patterns (already covered by 5 prior AO
entries in this repo) -- first test of the Saucer-specific pattern.

Signal logic
------------
- AO = SMA(median_price, ao_fast) - SMA(median_price, ao_slow)
  (median_price = (High+Low)/2; standard 5/34 defaults).
- Bullish saucer trigger at bar t: AO[t] > 0 AND AO[t-2] > AO[t-1] (red,
  declining) AND AO[t] > AO[t-1] (green, ticking up) -- i.e. the classic
  down-down-up 3-bar saucer shape entirely above the zero line.
- Long entry on the saucer trigger bar's close.
- Exit: AO crosses back below zero (trend invalidated), OR a
  max_hold_days time-stop (avoid indefinite holds through a stalling
  trend).
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _awesome_oscillator(df: pd.DataFrame, ao_fast: int, ao_slow: int) -> pd.Series:
    median_price = (df["high"] + df["low"]) / 2.0
    return median_price.rolling(ao_fast).mean() - median_price.rolling(ao_slow).mean()


def generate_signals(
    price_df: pd.DataFrame,
    ao_fast: int = 5,
    ao_slow: int = 34,
    max_hold_days: int = 25,
) -> pd.Series:
    df = _prep(price_df)
    ao = _awesome_oscillator(df, ao_fast=ao_fast, ao_slow=ao_slow)

    above_zero = ao > 0
    down_leg = ao.shift(2) > ao.shift(1)  # bar t-2 -> t-1 declined (red)
    up_leg = ao > ao.shift(1)  # bar t-1 -> t ticked up (green)
    saucer_trigger = (above_zero & down_leg & up_leg).fillna(False)

    exit_signal = (ao < 0).fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    entry_idx = -1
    for i in range(len(df)):
        if not in_pos:
            if bool(saucer_trigger.iloc[i]):
                in_pos = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
        else:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                position.iloc[i] = 0
                in_pos = False
            else:
                position.iloc[i] = 1

    return position.reindex(df.index).fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    ao_fast: int = 5,
    ao_slow: int = 34,
    max_hold_days: int = 25,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    position = generate_signals(
        price_df, ao_fast=ao_fast, ao_slow=ao_slow, max_hold_days=max_hold_days
    )
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
