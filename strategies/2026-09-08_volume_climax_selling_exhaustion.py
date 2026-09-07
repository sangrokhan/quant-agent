"""Strategy: Volume-Climax Selling Exhaustion Reversal (SMA + volume-multiple gate).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-126):
Per https://doc.stocksharp.com/en/api-examples/0115_Volume_Climax_Reversal
(fully disclosed reference strategy source code), a "selling climax" occurs
when a bearish candle (close < open) closes BELOW its own trailing N-period
SMA on volume exceeding `volume_multiplier`x the trailing N-period average
volume -- interpreted as the last wave of panic sellers exhausting the
move. Long entry at the close of that bar; exit when price crosses back
above the SMA (trend reversal confirmed) or a max-holding-period time-stop.
This is distinct from the already-tested/rejected Finveroo-sourced Volume
Climax Reversal (2026-09-06-157), which required BOTH a fresh 20-day price
low AND a lower-wick rejection candle shape in addition to the volume
spike -- this variant uses only the volume-multiple + close-below-SMA +
bearish-candle condition (no price-extreme or candle-wick-shape
requirement), a simpler and more frequently-triggering rule as literally
specified in the disclosed source code.

Signal logic
------------
- avg_volume: trailing `sma_period`-day average volume (prior day, not
  including today, matching the reference implementation's use of a
  rolling window excluding the newest bar for the threshold).
- is_volume_climax: today's volume > volume_multiplier * avg_volume.
- is_bearish: today's close < today's open.
- sma: trailing `sma_period`-day SMA of close.
- Entry (long): is_volume_climax AND is_bearish AND close < sma (selling
  climax below the trend average).
- Exit: close crosses back above the sma (mean-reversion/trend-flip
  confirmed), OR max_hold_days elapses.
- Flat otherwise, long-only, one position at a time.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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
    sma_period: int = 20,
    volume_multiplier: float = 2.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, open_, volume = df["close"], df["open"], df["volume"]

    avg_volume = volume.rolling(sma_period).mean().shift(1)
    is_volume_climax = volume > (volume_multiplier * avg_volume)
    is_bearish = close < open_
    sma = close.rolling(sma_period).mean()

    entry = is_volume_climax.fillna(False) & is_bearish & (close < sma)
    exit_signal = close > sma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
