"""Strategy: Upside Gap Two Crows (bullish continuation reading).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-274):
Per QuantifiedStrategies.com's "75 Types of Candlestick Patterns" list
(https://www.quantifiedstrategies.com/types-candlestick-patterns/, same
source already used in this repo for the Unique Three Rivers
bearish-continuation reframe, 2026-09-21-233), the "Upside Gap Two Crows"
pattern is TRADITIONALLY classified as a bearish reversal, but the
source's own stated reading is that "some traders instead use it as a
continuation pattern" -- and its own economic reasoning for the pattern
(bulls and bears "take turns" pushing price, with bulls initiating both
gaps and closing the whole 3-bar sequence still above bar1's close) leads
the source to conclude "this balance is a sign the price might wander the
path of least resistance, which is to the upside." This strategy
operationalizes that source-stated BULLISH continuation reading (not the
traditional bearish-reversal textbook label), matching the source's exact
disclosed 3-candle structure. First Upside Gap Two Crows entry in this
repo (0 prior hits) -- distinct from Unique Three Rivers (that pattern's
bar2 makes a LOWER low than bar1, i.e. downward drift; here bar2/bar3 both
gap UP from the prior candle, i.e. upward drift, despite both closing
bearish individually) and from the Three Black Crows family (no
gap-up-then-bearish-close alternation).

Signal logic
------------
- Bar1 (t-2): tall bullish candle -- close[t-2] > open[t-2], body size >=
  long_body_mult * its own trailing atr_window-bar average true range.
- Bar2 (t-1): gaps above bar1's high (open[t-1] > high[t-2], source's
  "gaps above the first candle") but closes bearish (close[t-1] <
  open[t-1]).
- Bar3 (t): gaps up above bar2's open (open[t] > open[t-1], source's "the
  third candle gaps up again") and is bearish (close[t] < open[t]),
  engulfing bar2's body (close[t] < close[t-1]), but its close remains
  ABOVE bar1's close (close[t] > close[t-2], source's disclosed condition
  that leaves the sequence net-bullish overall).
- Entry: long at bar3's own close once all of the above hold (source's own
  stated bullish-continuation bias for the completed 3-bar sequence).
- Exit: close crosses back below bar1's close (source's own reference
  level that defined the pattern's bullish bias) OR max_hold_days
  reached, whichever comes first.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position series)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    long_body_mult: float = 0.5,
    atr_window: int = 14,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    ``long_body_mult`` default lowered to 0.5 (from an initial 1.0) after
    this iteration's feasibility check found the full 7-condition pattern
    (gap-up bar2/bar3 + bearish bar2/bar3 + bar3-engulfs-bar2 +
    bar3-close-above-bar1-close) already only fires 9 times on QQQ
    2010-2026 even with NO body-size filter at all -- a >=1.0x-ATR "tall"
    requirement on bar1 was too strict on top of that and produced 0
    trades. 0.5x ATR keeps a meaningful "tall" filter while preserving a
    testable (if still small) sample.
    """
    df = _prep(price_df)
    idx = df.index
    n = len(idx)

    open_ = df["open"]
    high = df["high"]
    close = df["close"]

    atr = _atr(df, atr_window)
    body = (close - open_).abs()

    bar1_bullish_tall = (close > open_) & (body >= long_body_mult * atr)
    bar1_bullish_tall_2ago = bar1_bullish_tall.shift(2)

    open1_2ago = open_.shift(2)  # unused placeholder to keep naming clear
    close1_2ago = close.shift(2)
    high1_2ago = high.shift(2)

    bar2_gap_above_bar1 = open_.shift(1) > high1_2ago
    bar2_bearish = close.shift(1) < open_.shift(1)

    bar3_gap_above_bar2_open = open_ > open_.shift(1)
    bar3_bearish = close < open_
    bar3_engulfs_bar2 = close < close.shift(1)
    bar3_close_above_bar1_close = close > close1_2ago

    entry_signal = (
        bar1_bullish_tall_2ago
        & bar2_gap_above_bar1
        & bar2_bearish
        & bar3_gap_above_bar2_open
        & bar3_bearish
        & bar3_engulfs_bar2
        & bar3_close_above_bar1_close
    ).fillna(False)

    exit_ref_level = close1_2ago.where(entry_signal).ffill()

    position = pd.Series(0, index=idx, dtype=int)
    in_pos = False
    hold_bars = 0
    ref_level = None
    for i in range(n):
        if in_pos:
            hold_bars += 1
            if close.iloc[i] < ref_level or hold_bars >= max_hold_days:
                in_pos = False
                hold_bars = 0
                ref_level = None
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_pos = True
                hold_bars = 0
                ref_level = close1_2ago.iloc[i]
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    long_body_mult: float = 0.5,
    atr_window: int = 14,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df, long_body_mult=long_body_mult, atr_window=atr_window, max_hold_days=max_hold_days
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
