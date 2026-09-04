"""Strategy: Rolling-mean Z-score mean reversion with time-stop exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-082):
Per changelly.com's crypto mean-reversion guide, price deviations from a
rolling moving-average mean can be measured with a z-score
((close - rolling_mean) / rolling_std); a z-score below -2 signals an
oversold extreme worth a long mean-reversion entry, exiting when price
reverts back to the moving average (z crosses back above ~0) OR, if
reversion doesn't happen within a fixed window (the source recommends
5-10 days), a time-based exit to preserve capital regardless. This is
distinct from every previously-tested mean-reversion variant in this repo
(Bollinger Bands -001/-002, CCI -??? , RSI2 -005) because it uses a raw
rolling z-score of price itself (not a banded/normalized oscillator
derived differently) as both the entry trigger and the reference level for
the exit target.

Signal logic
------------
- rolling_mean = SMA(close, window)
- rolling_std = STD(close, window)
- z = (close - rolling_mean) / rolling_std
- Entry (long): z crosses below -entry_z (e.g. -2.0), i.e. today's z <
  -entry_z and yesterday's z >= -entry_z (fresh cross, avoid re-entering
  every day while still extreme).
- Exit: z crosses back above exit_z (default 0.0, i.e. price reverts to
  the moving average), OR max_hold_days elapses since entry, whichever
  comes first.
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


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 20,
    entry_z: float = 2.0,
    exit_z: float = 0.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rolling_mean = close.rolling(window).mean()
    rolling_std = close.rolling(window).std()
    z = (close - rolling_mean) / rolling_std

    z_prev = z.shift(1)
    entry_trigger = (z < -entry_z) & (z_prev >= -entry_z)

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        zi = z.iloc[i]
        if in_pos:
            hold_count += 1
            reverted = (zi >= exit_z) if pd.notna(zi) else False
            if reverted or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]) if pd.notna(entry_trigger.iloc[i]) else False:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    window: int = 20,
    entry_z: float = 2.0,
    exit_z: float = 0.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df, window=window, entry_z=entry_z, exit_z=exit_z, max_hold_days=max_hold_days
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
