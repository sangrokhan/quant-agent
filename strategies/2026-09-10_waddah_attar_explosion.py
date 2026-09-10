"""Strategy: Waddah Attar Explosion (WAE) momentum-vs-volatility breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-XXX):
Per keenbase-trading.com's WAE explainer (visited this iteration,
https://www.keenbase-trading.com/how-to-use-waddah-attar-explosion/) and
corroborated by search snippets from cTrader/ClickAlgo describing the
standard open-source WAE construction: WAE combines (1) a MACD-derived
momentum term -- the bar-over-bar CHANGE in the MACD line (fast EMA minus
slow EMA), scaled by a sensitivity multiplier, colored green when
positive / red when negative -- with (2) an "Explosion line" derived from
Bollinger Band width (upper - lower band, channel_length/bb_mult), and (3)
a "Dead Zone" volatility-floor threshold (ATR-based, per the source's own
note that later ports use "a true-range-based threshold"). Source's own
disclosed setup criterion: "the relevant histogram [is] above both the
Explosion line and the Dead Zone" with "an expanding histogram and an
expanding Explosion line" for a stronger setup.

This iteration operationalizes the long-only version: entry when the
green (bullish) momentum term exceeds BOTH the Explosion line AND the
Dead Zone threshold simultaneously (source's own compound "above both"
criterion); exit when momentum drops back below either the Explosion line
or the Dead Zone, or a max_hold_days time-stop. First WAE strategy in this
repo -- distinct from every plain MACD-histogram or Bollinger-Bandwidth
strategy already tested since WAE specifically gates MACD-histogram
momentum against a live BB-width explosion threshold AND a separate
ATR-based dead-zone floor simultaneously (a 3-way compound condition,
not a 2-way one).

Signal logic
------------
- macd_line = EMA(close, fast_len) - EMA(close, slow_len)
- momentum[t] = (macd_line[t] - macd_line[t-1]) * sensitivity
- bb_basis = SMA(close, channel_len); bb_dev = bb_mult * STD(close, channel_len)
- explosion_line[t] = (bb_basis + bb_dev) - (bb_basis - bb_dev) = 2 * bb_dev
- dead_zone[t] = rolling_mean(ATR(high, low, close, atr_len), dead_zone_len) * dead_zone_mult
- Entry (long): momentum > 0 AND momentum > explosion_line AND momentum > dead_zone.
- Exit: momentum <= explosion_line OR momentum <= dead_zone OR momentum <= 0,
  OR max_hold_days time-stop.

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


def _atr(df: pd.DataFrame, atr_len: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(atr_len).mean()


def generate_signals(
    price_df: pd.DataFrame,
    fast_len: int = 20,
    slow_len: int = 40,
    sensitivity: float = 150.0,
    channel_len: int = 20,
    bb_mult: float = 2.0,
    atr_len: int = 14,
    dead_zone_len: int = 100,
    dead_zone_mult: float = 3.7,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ema_fast = close.ewm(span=fast_len, adjust=False).mean()
    ema_slow = close.ewm(span=slow_len, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    momentum = (macd_line - macd_line.shift(1)) * sensitivity

    bb_basis = close.rolling(channel_len).mean()
    bb_dev = bb_mult * close.rolling(channel_len).std()
    explosion_line = 2.0 * bb_dev

    atr = _atr(df, atr_len)
    dead_zone = atr.rolling(dead_zone_len, min_periods=atr_len).mean() * dead_zone_mult

    entry = (momentum > 0) & (momentum > explosion_line) & (momentum > dead_zone)
    exit_condition = (momentum <= explosion_line) | (momentum <= dead_zone) | (momentum <= 0)

    entry = entry.fillna(False)
    exit_condition = exit_condition.fillna(True)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_condition.iloc[i]) or held >= max_hold_days:
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
