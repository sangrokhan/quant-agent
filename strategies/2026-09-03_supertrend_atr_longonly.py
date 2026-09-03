"""Strategy: Long-only SuperTrend (ATR-based flip) trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-014):
Source: Google AI-overview summary of the standard SuperTrend indicator
(fetched via browser_exec after web_search returned no results for this
keyword). Core rules: SuperTrend = ATR-based dynamic support/resistance band
(ATR period 10-14, multiplier ~3 by default) that flips direction (up-band
<-> down-band) based on price crossing it; long when price closes above the
SuperTrend line and the line has flipped from down(red) to up(green); the
line itself doubles as a trailing stop.

This is the first ATR-volatility-ADAPTIVE trend/breakout indicator tested in
this repo -- distinct from the Donchian channel breakout (2026-09-03-008,
pure price-level rolling max/min, not ATR-scaled) and from the fixed-lookback
SMA/momentum trend filters used elsewhere (2026-09-01-001, 2026-09-03-004,
2026-09-03-012), because the SuperTrend band width adapts to current
volatility (ATR) rather than using a fixed window of price levels or a fixed
trailing-return threshold.

Signal logic (long-only, per SAFETY.md -- no shorting)
------------
- ATR(atr_period) via Wilder's method (rolling mean of true range for
  simplicity, matching most public SuperTrend implementations' RMA/SMA
  choice closely enough for this backtest).
- basic_upperband = (high+low)/2 + multiplier * ATR
  basic_lowerband  = (high+low)/2 - multiplier * ATR
- final bands trail in the standard SuperTrend way (upperband only moves
  down or stays; lowerband only moves up or stays, each also resets when
  price crosses through it -- see `_supertrend` below for the exact
  recursive rule, matching the widely-published algorithm).
- direction flips to "up" the bar price closes above the final upperband,
  and to "down" the bar price closes below the final lowerband.
- Position: long (1) while direction == "up", flat (0) while direction ==
  "down". (No short leg -- SAFETY.md forbids nothing here since this is
  long/flat only, matching this repo's convention.)

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _supertrend_direction(
    high: pd.Series, low: pd.Series, close: pd.Series, atr_period: int, multiplier: float
) -> pd.Series:
    atr = _atr(high, low, close, atr_period)
    hl2 = (high + low) / 2.0
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr

    n = len(close)
    final_upper = pd.Series(np.nan, index=close.index)
    final_lower = pd.Series(np.nan, index=close.index)
    direction = pd.Series(1, index=close.index, dtype=int)  # 1 = up/long, -1 = down/flat

    for i in range(n):
        if i == 0 or np.isnan(atr.iloc[i]):
            final_upper.iloc[i] = basic_upper.iloc[i]
            final_lower.iloc[i] = basic_lower.iloc[i]
            direction.iloc[i] = 1
            continue

        prev_final_upper = final_upper.iloc[i - 1]
        prev_final_lower = final_lower.iloc[i - 1]
        prev_close = close.iloc[i - 1]

        cur_upper = basic_upper.iloc[i]
        if not np.isnan(prev_final_upper) and (cur_upper > prev_final_upper) and (prev_close <= prev_final_upper):
            cur_upper = prev_final_upper
        final_upper.iloc[i] = cur_upper

        cur_lower = basic_lower.iloc[i]
        if not np.isnan(prev_final_lower) and (cur_lower < prev_final_lower) and (prev_close >= prev_final_lower):
            cur_lower = prev_final_lower
        final_lower.iloc[i] = cur_lower

        prev_direction = direction.iloc[i - 1]
        if prev_direction == 1:
            direction.iloc[i] = -1 if close.iloc[i] < final_lower.iloc[i] else 1
        else:
            direction.iloc[i] = 1 if close.iloc[i] > final_upper.iloc[i] else -1

    return direction


def generate_signals(
    price_df: pd.DataFrame,
    atr_period: int = 10,
    multiplier: float = 3.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    direction = _supertrend_direction(high, low, close, atr_period, multiplier)
    position = (direction == 1).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
