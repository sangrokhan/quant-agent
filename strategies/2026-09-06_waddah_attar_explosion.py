"""Strategy: Waddah Attar Explosion (WAE) -- MACD-momentum "trend power"
gated by a Bollinger-Band-width explosion line and an ATR-based dead zone.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-104):
Per LuxAlgo's Waddah Attar Explosion library page: "trend power" is the
bar-to-bar change of a 20/40 EMA MACD line scaled by a sensitivity factor
(150); "explosion line" is the width of a 20-period, 2-std Bollinger Band;
a "dead zone" noise floor is derived from ATR(100)*3.7. Trading rule:
"Column breaks above the explosion line (clear of the dead zone): momentum
expanding faster than the volatility envelope -- the go condition,"
and "Color flip: pressure changed sides -- green permits longs, red
permits shorts, in the classic reading." This combines both gates: long
entry when trend power is positive (green, MACD line rising) AND its
absolute value exceeds both the explosion line and the dead zone
threshold simultaneously (the full WAE "go" condition). Novel indicator
family for this repo -- no prior Waddah Attar Explosion entries in the
knowledge base.

Source: https://www.luxalgo.com/library/indicator/waddah-attar-explosion/

Signal logic
------------
- macd_line = EMA(close, fast_len) - EMA(close, slow_len)
- trend_power = (macd_line - macd_line.shift(1)) * sensitivity
- bb_std = rolling std of close over bb_window; explosion_line =
  2 * bb_mult * bb_std (Bollinger Band width in price-change-scaled units,
  matching trend_power's scale since trend_power is itself a MACD delta)
- dead_zone = ATR(atr_window) * atr_mult
- Entry (long): trend_power > 0 (green) AND trend_power > explosion_line
  AND trend_power > dead_zone (full "go" condition, momentum clears both
  gates).
- Exit: trend_power drops back below either gate, or a max_hold_days
  time-stop.
- Flat otherwise.

Interface contract: both generate_signals and generate_returns accept all
tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    fast_len: int = 20,
    slow_len: int = 40,
    sensitivity: float = 150.0,
    bb_window: int = 20,
    bb_mult: float = 2.0,
    atr_window: int = 100,
    atr_mult: float = 3.7,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    macd_line = close.ewm(span=fast_len, adjust=False).mean() - close.ewm(
        span=slow_len, adjust=False
    ).mean()
    trend_power = (macd_line - macd_line.shift(1)) * sensitivity

    bb_std = close.rolling(bb_window).std()
    explosion_line = 2 * bb_mult * bb_std

    dead_zone = _atr(high, low, close, atr_window) * atr_mult

    go_condition = (trend_power.abs() > explosion_line) & (trend_power.abs() > dead_zone)
    entry = (go_condition & (trend_power > 0)).fillna(False)
    exit_signal = (~go_condition | (trend_power <= 0)).fillna(True)

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
