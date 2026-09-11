"""Strategy: Bollinger Band upper-band breakout confirmed by MACD bullish
crossover (trend-following combo).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-095):
Per QuantifiedStrategies.com's "MACD and Bollinger Bands Strategy - Trading
Rules, Setup, Backtest (78% Win Rate)"
(https://www.quantifiedstrategies.com/macd-and-bollinger-bands-strategy/,
visited 2026-09-11), source's own disclosed "Trend-Following Strategy"
rule: "A buy signal occurs when the price breaks above the upper Bollinger
Band, and the MACD line crosses above the signal line, indicating upward
momentum." Distinct from the prior repo BB+MACD variant
(2026-09-06-154, lower-band-touch MEAN-REVERSION confirmation, entry
requires price near the LOWER band) -- this is the opposite mechanic: an
UPPER-band breakout TREND-FOLLOWING entry, using MACD as a momentum
confirmation gate rather than a bounce-timing signal.

Signal logic
------------
- Bollinger Bands: SMA(bb_window) +/- bb_std * rolling std.
- MACD: EMA(macd_fast) - EMA(macd_slow), signal = EMA(macd_signal) of that
  line (standard 12/26/9 defaults).
- Entry (long): close crosses above the upper Bollinger Band AND the MACD
  line is above its signal line (momentum confirmation, source's own
  "crosses above" language interpreted here as "is above" to allow same-
  day co-occurrence rather than requiring the exact crossover bar to
  coincide with the breakout bar -- tested at strictness in the grid).
- Exit: close crosses back below the middle band (SMA), MACD crosses back
  below its signal line, or a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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
    bb_window: int = 20,
    bb_std: float = 2.0,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    upper_band = sma + bb_std * std

    ema_fast = close.ewm(span=macd_fast, adjust=False).mean()
    ema_slow = close.ewm(span=macd_slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=macd_signal, adjust=False).mean()
    macd_bullish = macd_line > signal_line

    breakout = (close > upper_band) & (close.shift(1) <= upper_band.shift(1))
    entry = breakout & macd_bullish.fillna(False)

    exit_band = close < sma
    exit_macd = ~macd_bullish.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_band.iloc[i]) or bool(exit_macd.iloc[i]) or held >= max_hold_days:
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
