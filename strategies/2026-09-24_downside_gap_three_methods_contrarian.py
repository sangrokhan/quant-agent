"""Strategy: Bulkowski Downside Gap Three Methods candlestick, contrarian
bullish reversal (long-only) despite its "bearish continuation" name.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/dgtm.html (Thomas Bulkowski,
browser_exec fallback -- web_search's DDGS backend returns unrelated
results for this domain, confirmed again this iteration).

Source's own disclosed identification rules and statistics (a rare case
where the source's THEORY and TESTED reality directly diverge):
    "Look for two long black bodied candles in a downward price trend.
    The second candle should have a gap between them (shadows do not
    overlap). The last day is a white candle that opens within the body
    of the prior day and closes within the body of the first day, closing
    the gap between the two black candles."
    Theoretical performance: Bearish continuation.
    Tested performance: Bullish reversal 62% of the time.
    Overall performance rank: 26/103 (quite respectable).
    Source's own explicit trading guidance: "the downside gap three
    methods candlestick does best after downward breakouts... [but tests
    show it acts as] a bullish reversal 62% of the time" -- i.e. despite
    its bearish-sounding name and theoretical framing, price statistically
    REVERSES upward after this pattern in a downtrend. This strategy
    trades that disclosed empirical reality (contrarian long), not the
    pattern's own theoretical (bearish) framing -- the same "trade the
    source's own tested numbers, not its label" approach already used
    successfully elsewhere in this repo (e.g. Three Black Crows
    contrarian long, 2026-09-07-001).

First Downside Gap Three Methods strategy in this repo (0 prior KB index
hits) -- distinct from every other 3-candle pattern already tested
(Morning/Evening Star use a small indecision middle candle; Three Black
Crows requires 3 consecutive lower closes with body overlap; this pattern
requires a genuine NON-overlapping gap between candles 1-2 and a
gap-closing white candle 3).

Signal logic
------------
1. Downtrend context (source's own required setup): close[t-2] < 
   SMA(trend_window) at the pattern's start.
2. Candle 1 (t-2) and candle 2 (t-1): both bearish (close < open), real
   body >= min_body_pct of open (source's own "long black bodied"
   requirement).
3. True gap (shadows do not overlap): low[t-2] > high[t-1] (candle 2's
   entire range sits below candle 1's entire range).
4. Candle 3 (t): bullish (close > open), opens within candle 2's body
   (open[t-1] <= open[t] <= close[t-1], since candle 2 is bearish
   close[t-1] < open[t-1]) AND closes within candle 1's body
   (close[t-2] <= close[t] <= open[t-2]) -- source's own disclosed "closes
   within the body of the first day, closing the gap."
5. Entry: at candle 3's (t) own close once the pattern confirms (same
   confirmed-at-close convention as this repo's other candlestick
   strategies).
6. Exit: close falls below its own SMA(exit_sma_window) (reversal-
   continuation failure) OR a max_hold_days time-stop, whichever comes
   first -- same exit convention as this repo's other single-pattern-
   trigger candlestick strategies.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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
    min_body_pct: float = 0.01,
    exit_sma_window: int = 15,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    idx = df.index
    n = len(idx)

    open_ = df["open"]
    close = df["close"]
    high = df["high"]
    low = df["low"]

    sma_trend = close.rolling(trend_window).mean()
    downtrend = close.shift(2) < sma_trend.shift(2)

    c1_open, c1_close = open_.shift(2), close.shift(2)
    c1_high, c1_low = high.shift(2), low.shift(2)
    c2_open, c2_close = open_.shift(1), close.shift(1)
    c2_high, c2_low = high.shift(1), low.shift(1)

    c1_bearish = c1_close < c1_open
    c2_bearish = c2_close < c2_open
    c1_body_pct = (c1_open - c1_close) / c1_open.replace(0, pd.NA)
    c2_body_pct = (c2_open - c2_close) / c2_open.replace(0, pd.NA)
    c1_long_body = c1_body_pct >= min_body_pct
    c2_long_body = c2_body_pct >= min_body_pct

    true_gap = c1_low > c2_high

    c3_bullish = close > open_
    opens_in_c2_body = (open_ >= c2_close) & (open_ <= c2_open)
    closes_in_c1_body = (close >= c1_close) & (close <= c1_open)

    pattern_confirmed = (
        downtrend.fillna(False)
        & c1_bearish.fillna(False)
        & c2_bearish.fillna(False)
        & c1_long_body.fillna(False)
        & c2_long_body.fillna(False)
        & true_gap.fillna(False)
        & c3_bullish.fillna(False)
        & opens_in_c2_body.fillna(False)
        & closes_in_c1_body.fillna(False)
    )

    exit_sma = close.rolling(exit_sma_window).mean()

    position = pd.Series(0, index=idx, dtype=int)
    in_position = False
    entry_i = -1
    for i in range(n):
        if in_position:
            hold_days = i - entry_i
            trend_exit = close.iloc[i] < exit_sma.iloc[i] if pd.notna(exit_sma.iloc[i]) else False
            if trend_exit or hold_days >= max_hold_days:
                in_position = False
            else:
                position.iloc[i] = 1
        else:
            if bool(pattern_confirmed.iloc[i]):
                in_position = True
                entry_i = i
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
