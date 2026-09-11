"""Strategy: Hanging Man candlestick reversal short, RSI-overbought confirmed.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-116):
Per quantifiedstrategies.com's "Hanging Man Candlestick Pattern: Backtest
Results" article, the Hanging Man (small body near the top of the daily
range, long lower shadow >= 2x body, little/no upper shadow, occurring
during an established up-swing) signals sellers gaining momentum against
buyers at a local top. The source explicitly recommends NOT trading the
raw pattern alone ("it may be pretty useless by itself... must be used
with tools like ... momentum oscillators") and specifically describes a
mean-reversion variant: "If the Hanging Man pattern forms at a key
resistance level when the RSI is falling from an overbought level, a
mean-reversion trader can enter a short position and ride the anticipated
price decline to the moving average line."

This strategy implements exactly that mechanical combination:
  1. Uptrend context: close > SMA(trend_window) (the "upward price swing").
  2. Hanging Man candle: body <= body_max_pct of the day's range, lower
     shadow >= shadow_ratio * body, upper shadow <= body (little/no upper
     shadow).
  3. RSI(rsi_period) was >= rsi_overbought within the last rsi_lookback
     bars and is now falling (RSI today < RSI yesterday) -- "RSI falling
     from an overbought level."
  4. Entry: short at next bar's close when all three conditions align on
     the same/adjacent bars.
  5. Exit: close crosses back below/to the SMA(trend_window) ("ride the
     anticipated price decline to the moving average line"), or a
     max_hold_days time-stop (avoid indefinite holds), whichever first.

Distinct from prior candlestick-pattern entries in this repo (Three White
Soldiers, Morning Star, Piercing Line, Dark Cloud Cover, Tweezer, Inside
Bar, NR7/NR4 -- none of which is "Hanging Man", a zero-hit indicator
family in strategies_index.jsonl as of this iteration) and distinct from
prior RSI-overbought-reversal strategies (which typically fade RSI level
crosses alone, without a candlestick-shape confirmation gate).

Source: https://www.quantifiedstrategies.com/hanging-man-candlestick-pattern/
(read via browser_exec fallback this iteration; web_search DDGS backend
returned repeated TLS/connection errors on multiple queries).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (position: -1 short/0 flat)
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


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-12)
    return 100.0 - (100.0 / (1.0 + rs))


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    body_max_pct: float = 0.30,
    shadow_ratio: float = 2.0,
    rsi_period: int = 14,
    rsi_overbought: float = 70.0,
    rsi_lookback: int = 3,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {-1, 0} short/flat position series."""
    df = _prep(price_df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]

    sma = c.rolling(trend_window).mean()
    uptrend = c > sma

    rng = (h - l).replace(0.0, 1e-12)
    body = (c - o).abs()
    body_pct = body / rng
    upper_shadow = h - c.where(c >= o, o)
    lower_shadow = c.where(c >= o, o) - l
    # generalized for either candle color: lower shadow measured from min(open,close)
    lower_shadow = df[["open", "close"]].min(axis=1) - l
    upper_shadow = h - df[["open", "close"]].max(axis=1)

    is_hanging_man = (
        (body_pct <= body_max_pct)
        & (lower_shadow >= shadow_ratio * body.replace(0.0, 1e-12))
        & (upper_shadow <= body.replace(0.0, 1e-12) * 1.0 + 1e-9)
    )

    rsi = _rsi(c, rsi_period)
    was_overbought = rsi.rolling(rsi_lookback).max() >= rsi_overbought
    rsi_falling = rsi < rsi.shift(1)

    entry = uptrend.fillna(False) & is_hanging_man.fillna(False) & was_overbought.fillna(False) & rsi_falling.fillna(False)
    exit_meanrev = c <= sma

    position = pd.Series(0, index=c.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(c)):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = -1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = -1
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
