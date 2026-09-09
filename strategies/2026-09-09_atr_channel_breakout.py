"""Strategy: ATR Channel Breakout (baseline SMA +/- ATR multiplier bands).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-096):
Per Google AI-overview synthesis (TradingCode/TradingBlox/StockGro sources,
query "ATR channel breakout strategy exact entry exit rules"): a dynamic
volatility channel built from a long baseline moving average (350-day SMA
per TradingBlox's canonical Trading Blox ATR Channel Breakout System) plus
an ATR-derived band (Upper = baseline + multiplier*ATR(20), Lower =
baseline - multiplier*ATR(20), common multiplier range 3-7) triggers a
long entry when the close breaks completely above the upper channel
boundary; exit when price crosses back below the baseline moving average
(source's primary exit rule), backstopped here with a max_hold_days
time-stop.

First ATR-Channel-breakout (SMA baseline +/- ATR band, TradingBlox-style)
strategy in this repo -- distinct from plain Donchian breakout (rolling
high/low, no ATR band), Keltner Channel (EMA baseline, tighter multiplier
range ~1-2, mean-reversion/squeeze framing in this repo's prior variants),
and Chandelier Exit (trailing stop off swing high/low, not a breakout
entry trigger).

Signal logic
------------
- baseline = SMA(close, baseline_window) [source default: 350]
- atr = ATR(high, low, close, atr_window) [source default: 20]
- upper_channel = baseline + atr_mult * atr
- Entry (long): close crosses from at/below upper_channel to above it
  (breakout confirmation, avoids re-triggering every bar while already
  above the channel).
- Exit: close crosses back below baseline (source's primary "Baseline
  Crossover Exit" rule), OR a max_hold_days time-stop backstop.

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


def _atr(df: pd.DataFrame, window: int = 20) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    baseline_window: int = 350,
    atr_window: int = 20,
    atr_mult: float = 5.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    baseline = close.rolling(baseline_window).mean()
    atr = _atr(df, atr_window)
    upper_channel = baseline + atr_mult * atr

    above_upper = close > upper_channel
    entry = above_upper & (~above_upper.shift(1).fillna(False))
    exit_baseline = close < baseline

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_baseline.iloc[i]) or held >= max_hold_days:
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
