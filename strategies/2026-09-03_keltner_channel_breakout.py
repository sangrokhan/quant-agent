"""Strategy: Keltner Channel breakout, long-only (EMA midline + ATR bands).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-016):
Source: Google search snippets for Keltner Channel breakout strategy rules
(web_search failed with a DDGS/TLS connection error for this query, fell
back to browser_exec Google search). Standard Keltner Channel construction:
middle line = EMA(20), bands = middle line +/- multiplier * ATR(10).
TradingView's own summary snippet: "identify bullish breakouts when price
closes above the upper channel". Exit rule (not given verbatim in any
snippet, but standard/conventional for channel-midline systems, and
consistent with how this repo's Donchian -008 and SuperTrend -014 both use
a trend-filter/midline flip as the exit): exit when price closes back below
the EMA midline.

Distinct construction from SuperTrend (2026-09-03-014, a *flip-based*
trailing-stop line that only ever moves in the current trend's favor) and
from Donchian (2026-09-03-008, a pure price-level rolling max/min channel
with no volatility scaling) -- Keltner uses a fixed EMA midline with
symmetric ATR-scaled band width that does not trail/ratchet.

Signal logic (long-only, per SAFETY.md)
------------
- middle = EMA(ema_period)
- upper = middle + atr_multiplier * ATR(atr_period)
- Entry (long): close > upper (breakout above upper band).
- Exit: close < middle (EMA midline).
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


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def generate_signals(
    price_df: pd.DataFrame,
    ema_period: int = 20,
    atr_period: int = 10,
    atr_multiplier: float = 2.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    middle = close.ewm(span=ema_period, adjust=False).mean()
    atr = _atr(high, low, close, atr_period)
    upper = middle + atr_multiplier * atr

    entry = close > upper
    exit_signal = close < middle

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
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
