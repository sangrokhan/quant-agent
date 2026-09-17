"""Strategy: ATR Breakout Entries (Ken Calhoun, TASC May 2016; code
republished TASC Jun 2016 Traders Tips).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-135):
Per Ken Calhoun's "ATR Breakout Entries" (TASC May 2016; TradeStation
EasyLanguage code disclosed at
https://traders.com/Documentation/FEEDbk_docs/2016/06/TradersTips.html),
a strong swing-trading breakout is confirmed when THREE conditions align on
the same bar: (1) close crosses above its own moving_avg_length-day SMA
(source: 100-day), (2) today's ATR(atr_length) is the highest of the
trailing atr_lookback bars (volatility is currently expanding, not
contracting -- "ATRValue >= Highest(ATRValue[1], ATRLookBack)"), and
(3) today's bar range exceeds bar_size_multiplier x its own
bar_size_lookback-day average range (an outsized "breakout bar", source's
own "BarSizeOK" condition). The source's own exit is a fixed-dollar stop
loss (not replicable exactly with only OHLCV); this iteration substitutes a
mechanical exit of close crossing back below the same SMA, or a
max_hold_days time-stop.

Signal logic
------------
- sma = SMA(close, moving_avg_length).
- sma_cross = close crosses above sma (from <= to >).
- atr = Wilder ATR(atr_length).
- atr_expanding = atr >= rolling max of the trailing atr_lookback bars of
  atr (excluding today, per source's ATRValue[1]).
- avg_range = SMA(high-low, bar_size_lookback).
- bar_size_ok = (high - low) > avg_range * bar_size_multiplier.
- Entry (long): sma_cross AND atr_expanding AND bar_size_ok (all three on
  the same bar).
- Exit: close crosses back below sma, OR max_hold_days time-stop.
- Flat otherwise.

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


def _wilder_atr(df: pd.DataFrame, atr_length: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / atr_length, adjust=False, min_periods=atr_length).mean()


def generate_signals(
    price_df: pd.DataFrame,
    atr_length: int = 14,
    atr_lookback: int = 14,
    moving_avg_length: int = 100,
    bar_size_multiplier: float = 1.5,
    bar_size_lookback: int = 5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    sma = close.rolling(moving_avg_length).mean()
    sma_cross = (close > sma) & (close.shift(1) <= sma.shift(1))

    atr = _wilder_atr(df, atr_length)
    atr_prev_max = atr.shift(1).rolling(atr_lookback).max()
    atr_expanding = atr >= atr_prev_max

    bar_range = high - low
    avg_range = bar_range.rolling(bar_size_lookback).mean()
    bar_size_ok = bar_range > (avg_range * bar_size_multiplier)

    entry = sma_cross.fillna(False) & atr_expanding.fillna(False) & bar_size_ok.fillna(False)
    exit_sma_flip = close < sma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_sma_flip.iloc[i]) or held >= max_hold_days:
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
