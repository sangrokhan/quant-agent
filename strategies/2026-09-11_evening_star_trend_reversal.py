"""Strategy: Evening Star three-candle bearish reversal short, trend-confirmed.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-117):
Per quantifiedstrategies.com's "Evening Star Candlestick Pattern: Backtest
Analysis" article, the Evening Star is a three-candle bearish reversal
pattern: (1) a tall bullish candle in an ongoing up-swing, (2) a small
"indecision" candle that gaps above candle 1's body, (3) a bearish candle
that closes below the midpoint of candle 1's body. The source frames it as
the bearish counterpart of the (already-tested-in-this-repo) Three White
Soldiers/Morning Star bullish patterns, and explicitly recommends
confirming with "trendlines, resistance levels, and momentum oscillators"
before shorting -- we use a simple uptrend filter (close > SMA(trend_window))
as the "ongoing upward price swing" context requirement, matching the
source's own framing that the pattern is only meaningful "at the top of an
upward price swing."

Mechanical rule implemented:
  - Candle 1 (2 bars ago): bullish (close>open), body size >= tall_body_pct
    of its own high-low range (a "tall" candle).
  - Candle 2 (1 bar ago): body midpoint gaps above candle 1's body top
    (min gap = gap_min_pct * candle 1's body size) -- the "small candle
    that gaps above."
  - Candle 3 (current bar): bearish (close<open), closes below the
    midpoint of candle 1's body ((open1+close1)/2).
  - Uptrend context: close (candle 1's close) > SMA(trend_window).
  - Entry: short at candle 3's close when all three candles + uptrend
    context align.
  - Exit: close crosses back above the SMA(trend_window) (support/
    resistance reclaim invalidates the reversal), or a max_hold_days
    time-stop.

Distinct from prior candlestick-pattern entries: Morning Star (bullish
mirror, already tested), Three White Soldiers (already tested), Dark Cloud
Cover / Piercing Line (2-candle patterns, already tested) -- Evening Star
itself has zero prior hits in strategies_index.jsonl as of this iteration.

Source: https://www.quantifiedstrategies.com/evening-star-candlestick-pattern/
(read via browser_exec fallback this iteration; web_search DDGS backend
continues returning TLS/connection errors on all queries this cron trigger).

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


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    tall_body_pct: float = 0.55,
    gap_min_pct: float = 0.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {-1, 0} short/flat position series."""
    df = _prep(price_df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]

    sma = c.rolling(trend_window).mean()

    rng1 = (h - l).shift(2).replace(0.0, 1e-12)
    o1, c1 = o.shift(2), c.shift(2)
    body1 = (c1 - o1)
    is_bullish1 = body1 > 0
    is_tall1 = (body1.abs() / rng1) >= tall_body_pct
    body1_top = pd.concat([o1, c1], axis=1).max(axis=1)
    body1_mid = (o1 + c1) / 2.0

    o2, c2 = o.shift(1), c.shift(1)
    body2_bottom = pd.concat([o2, c2], axis=1).min(axis=1)
    gaps_above = body2_bottom >= body1_top + gap_min_pct * body1.abs()

    is_bearish3 = c < o
    closes_below_mid1 = c < body1_mid

    uptrend = c1 > sma.shift(2)

    entry = (
        is_bullish1.fillna(False)
        & is_tall1.fillna(False)
        & gaps_above.fillna(False)
        & is_bearish3.fillna(False)
        & closes_below_mid1.fillna(False)
        & uptrend.fillna(False)
    )

    exit_trend_reclaim = c > sma

    position = pd.Series(0, index=c.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(c)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trend_reclaim.iloc[i]) or held >= max_hold_days:
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
