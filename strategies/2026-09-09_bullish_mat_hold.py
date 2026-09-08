"""Strategy: Bullish Mat Hold (5-candle trend-continuation pattern).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-035):
Per wrtrading.com's Mat Hold Candlestick Pattern guide (read this cron
trigger): the Mat Hold is a 5-candle TREND-CONTINUATION pattern (source
claims a "67-78%" historical success rate), fundamentally distinct from
every reversal candlestick pattern already tested in this repo (Bullish
Engulfing, Hammer, Piercing Line, Harami, Tweezer Bottom, Belt Hold, Three
Outside Up, etc.) since it requires an established UPTREND that continues,
not a downtrend reversal:
    1. Candle 1: a strong bullish impulse candle (aligned with the prior
       uptrend, signaling clear momentum).
    2. Candles 2-4: three smaller-bodied candles forming a brief
       consolidation/pullback that stays structurally ABOVE candle 1's
       low (may dip slightly but the range holds).
    3. Candle 5: a bullish breakout candle that closes decisively above
       the consolidation's high (approximately candle 1's own high),
       confirming the trend resumes.

Signal logic
------------
- Uptrend context: close[i-4] (candle 1) above SMA(trend_window).
- Candle 1 (bar i-4): bullish (close > open) with a real body >=
  impulse_body_mult * the average real body of the preceding
  body_lookback bars (a "strong" impulse candle, per source's own
  qualitative description).
- Candles 2-4 (bars i-3, i-2, i-1): each stays above candle 1's low
  (low[j] >= low[i-4] * (1 - consolidation_tolerance)) -- the source's
  "holds above the low of the first candle" structural requirement.
- Candle 5 (bar i): bullish (close > open); close[i] > high of candle 1
  (breakout above the consolidation range, per source's "closing above
  the consolidation" confirmation).
- Entry: on candle 5's close (the pattern completes on this bar).
- Exit: close crosses back below candle 1's low (structural failure), or
  a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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
    trend_window: int = 50,
    body_lookback: int = 20,
    impulse_body_mult: float = 1.3,
    consolidation_tolerance: float = 0.01,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    open_, high, low, close = df["open"], df["high"], df["low"], df["close"]
    trend_sma = close.rolling(trend_window, min_periods=trend_window).mean()
    real_body = (close - open_).abs()
    avg_body = real_body.rolling(body_lookback, min_periods=body_lookback).mean()

    n = len(df)
    o = open_.values
    h = high.values
    l = low.values
    c = close.values
    sma = trend_sma.values
    ab = avg_body.values

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = 0.0

    for i in range(4, n):
        if in_position:
            held = i - entry_idx
            if c[i] < stop_price or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        i1 = i - 4  # candle 1
        if pd.isna(sma[i1]) or pd.isna(ab[i1]) or ab[i1] <= 0:
            continue

        c1_bullish = c[i1] > o[i1]
        c1_body = abs(c[i1] - o[i1])
        c1_strong = c1_body >= impulse_body_mult * ab[i1]
        uptrend = c[i1] > sma[i1]

        c1_low = l[i1]
        c1_high = h[i1]

        consolidation_holds = all(
            l[j] >= c1_low * (1 - consolidation_tolerance) for j in (i - 3, i - 2, i - 1)
        )

        c5_bullish = c[i] > o[i]
        c5_breakout = c[i] > c1_high

        if c1_bullish and c1_strong and uptrend and consolidation_holds and c5_bullish and c5_breakout:
            in_position = True
            entry_idx = i
            stop_price = c1_low
            position.iloc[i] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
