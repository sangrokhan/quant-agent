"""Strategy: Apirine On-Balance Volume Modified (OBVM) signal-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-156):
Vitali Apirine's Traders' Tips article (TASC Apr 2020, "On-Balance Volume
Modified (OBVM)", source: Traders.com Apr 2020 Traders' Tips, TradeStation
EasyLanguage code read this iteration) smooths the classic Granville
on-balance-volume (OBV) cumulative volume-flow indicator with an EMA, then
adds an EMA signal line to it -- structurally a "MACD applied to OBV
instead of price". A bullish crossover (OBVM crosses above its signal line)
should mark a volume-flow momentum shift toward accumulation; this is
distinct from every prior OBV-family strategy in this repo since none apply
a signal-line crossover directly to a smoothed OBV (as opposed to raw OBV
divergence, OBV z-score, or OBV vs SMA).

Formula (per source)
---------------------
- OBV = cumulative running sum of volume, added when close > prior close,
  subtracted when close < prior close, unchanged when equal (classic
  Granville OBV).
- OBVM = EMA(OBV, obvm_length)
- SignalLine = EMA(OBVM, signal_length)

Signal logic (long-only adaptation; original also shorts on the bearish
cross, adapted here to repo's long/flat convention)
------------------------------------------------------------------------
- Entry (long): OBVM crosses above SignalLine.
- Exit: OBVM crosses below SignalLine, OR after `max_hold_days`.
- No short leg.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff().fillna(0.0))
    signed_vol = direction * volume
    return signed_vol.cumsum()


def generate_signals(
    price_df: pd.DataFrame,
    obvm_length: int = 7,
    signal_length: int = 10,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    obv = _obv(close, volume)
    obvm = obv.ewm(span=obvm_length, adjust=False).mean()
    signal_line = obvm.ewm(span=signal_length, adjust=False).mean()

    bullish_cross = (obvm.shift(1) <= signal_line.shift(1)) & (obvm > signal_line)
    bearish_cross = (obvm.shift(1) >= signal_line.shift(1)) & (obvm < signal_line)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    warmup = obvm_length + signal_length
    for i in range(len(close)):
        if i < warmup:
            position.iloc[i] = 0
            continue
        if in_position:
            held = i - entry_idx
            if bool(bearish_cross.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(bullish_cross.iloc[i]):
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
