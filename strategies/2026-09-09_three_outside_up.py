"""Strategy: Three Outside Up (3-candle bullish reversal, engulfing + confirmation).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-034):
Per Investopedia's "3 Outside Up/Down Signals" explainer
(https://www.investopedia.com/terms/t/three-outside-updown.asp), the Three
Outside Up is a bullish 3-candle reversal pattern distinct from this repo's
already-tested 2-candle Bullish Engulfing (2026-09-04-102, rejected; volume
-gated variant 2026-09-08-024, also rejected):
    1. The market is in a downtrend.
    2. Candle 1 is bearish.
    3. Candle 2 is bullish with a long real body that FULLY CONTAINS
       (engulfs) candle 1's real body -- identical to a standard bullish
       engulfing.
    4. Candle 3 is bullish with a close HIGHER than candle 2's close --
       an explicit third confirmation/acceleration candle that plain
       Bullish Engulfing strategies in this repo do NOT require.
Source's own framing: "these patterns should be used with other indicators
for confirmation" and are described as "reliable indicators of a
reversal" occurring "frequently" -- this iteration tests the pattern
exactly as literally defined (the 3rd-candle requirement IS the
confirmation), rather than adding yet another external filter.

Signal logic
------------
- Downtrend context: close[i-2] (candle 1's own close, i.e. the day before
  the engulfing candle) below SMA(trend_window).
- Candle 1 (bar i-2): bearish (close < open).
- Candle 2 (bar i-1): bullish (close > open); real body fully contains
  candle 1's real body (open[i-1] <= min(open[i-2],close[i-2]) AND
  close[i-1] >= max(open[i-2],close[i-2])).
- Candle 3 (bar i): bullish (close > open); close[i] > close[i-1] (the
  defining confirmation/acceleration requirement).
- Entry: on candle 3's close (the pattern completes on this bar).
- Exit: close crosses back below candle 1's low (pattern failure/stop),
  or a max_hold_days time-stop.

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
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    open_, high, low, close = df["open"], df["high"], df["low"], df["close"]
    trend_sma = close.rolling(trend_window, min_periods=trend_window).mean()

    n = len(df)
    o = open_.values
    h = high.values
    l = low.values
    c = close.values
    sma = trend_sma.values

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = 0.0

    for i in range(2, n):
        if in_position:
            held = i - entry_idx
            if c[i] < stop_price or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        if pd.isna(sma[i - 2]):
            continue

        c1_bearish = c[i - 2] < o[i - 2]
        c1_low, c1_high_body = min(o[i - 2], c[i - 2]), max(o[i - 2], c[i - 2])
        downtrend = c[i - 2] < sma[i - 2]

        c2_bullish = c[i - 1] > o[i - 1]
        c2_engulfs = (o[i - 1] <= c1_low) and (c[i - 1] >= c1_high_body)

        c3_bullish = c[i] > o[i]
        c3_higher_close = c[i] > c[i - 1]

        if c1_bearish and downtrend and c2_bullish and c2_engulfs and c3_bullish and c3_higher_close:
            in_position = True
            entry_idx = i
            stop_price = l[i - 2]  # candle 1's low
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
