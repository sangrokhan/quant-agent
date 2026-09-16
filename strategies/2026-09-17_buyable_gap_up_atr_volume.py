"""Strategy: Buyable Gap-Up (BGU, Kacher/Morales) with ATR-scaled gap
threshold and volume confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-014):
Per the "OWL Handbook" (Gil Morales & Chris Kacher), disclosed verbatim via
Scribd (https://www.scribd.com/document/The-Owl-Handbook-Timeless-Trading-Methods,
read via browser_exec this iteration after Google search fallback): "A
buyable gap-up is characterized by a price move that is at least 0.75 times
the 40-day Average True Range of the stock, with volume on the gap-up at
least [1.5x average volume]." A gap-up is a genuine market-structure event
(open significantly above the prior close, typically driven by earnings or
major news) distinct from the Pocket Pivot pattern (2026-09-17-012/013,
already tested this cron trigger) which flags accumulation happening
QUIETLY inside a base -- BGU is the opposite: an OVERT, high-conviction,
one-day institutional buying event.

This is the FIRST Buyable Gap-Up strategy in this repo (0 prior entries) --
distinct from the ~14 prior gap-based strategies already tested (gap fade,
gap continuation, gap-and-go, exhaustion gap, weekend gap sweep, etc.),
none of which use an ATR-relative gap-size threshold combined with a
volume-multiple confirmation specifically per Kacher/Morales' disclosed
definition.

Signal logic
------------
- Gap-up day: today's open - yesterday's close >= gap_atr_mult * ATR(40)
  (computed on yesterday's data, avoiding look-ahead), AND today's volume
  >= volume_mult * its own trailing 50-day average volume, AND today
  closes above its own open (confirms the gap wasn't immediately faded).
- Long entry at the qualifying gap-up day's close.
- Exit: close falls below the gap-up day's own LOW (the classical "porosity"
  stop -- the source explicitly notes a BGU that gets filled/violated on
  the downside has failed), or a max_hold_days time-stop backstop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    tr = _true_range(high, low, close)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def generate_signals(
    price_df: pd.DataFrame,
    atr_period: int = 40,
    gap_atr_mult: float = 0.75,
    volume_window: int = 50,
    volume_mult: float = 1.5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"]

    atr = _atr(high, low, close, atr_period)
    avg_volume = volume.rolling(volume_window).mean()

    gap_size = open_ - close.shift(1)
    gap_up_rule = gap_size >= (gap_atr_mult * atr.shift(1))
    volume_rule = volume >= (volume_mult * avg_volume.shift(1))
    closes_up = close > open_

    bgu = gap_up_rule.fillna(False) & volume_rule.fillna(False) & closes_up
    bgu_low = low.where(bgu)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_level = None
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(close.iloc[i] < stop_level) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                stop_level = None
                continue
            position.iloc[i] = 1
        else:
            if bool(bgu.iloc[i]):
                in_position = True
                entry_idx = i
                stop_level = float(bgu_low.iloc[i])
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
