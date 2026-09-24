"""Strategy: Bulkowski Last Engulfing Bottom candlestick, contrarian short
(trading the source's own disclosed tested reality, not its bullish name),
filtered by the source's disclosed best-performing context.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/LastEngulfBottom.html (Thomas
Bulkowski, browser_exec fallback -- web_search's DDGS backend cannot
usefully extract this domain, as with every prior thepatternsite.com entry
this cron trigger).

Source's own disclosed identification rules and statistics (another case
where the source's THEORY and TESTED reality directly diverge, like
Downside Gap Three Methods 2026-09-24-118 earlier this run):
    "Look for a white candle on the first day in a downward price trend
    followed by a black candle that engulfs the body of the white
    candle... The black candle has a body that is above the top and below
    the bottom of the white candle. Ignore the shadows."
    Theoretical performance: bullish reversal.
    Tested performance: bearish CONTINUATION 65% of the time (source's own
    explicit reasoning: "the tall black candle is bearish and price is
    closer to the bottom of the candle pattern than the top... a downward
    breakout would be a continuation of that downtrend").
    Frequency rank: 13/103 (common). Overall performance rank: 48/103
    (mediocre trend strength after breakout).

Source's own "Three Trading Tidbits" (book p.473/475) disclose two
performance-boosting refinements used here:
    1. "Last engulfing bottom candles that appear within a third of the
       yearly low perform best" -- p.473.
    2. "For the best performance, trade this candle as part of a downward
       RETRACEMENT of the upward price trend" -- p.475 (i.e. NOT a raw
       primary downtrend -- a pullback inside a larger uptrend), the same
       source-preferred context already used successfully for Above the
       Stomach (2026-09-24-116) and attempted for Takuri Line
       (2026-09-24-117, rejected on feasibility) earlier this cron
       trigger.

This strategy trades the disclosed empirical reality (contrarian SHORT on
confirmed breakdown below the pattern) within the source's own two
disclosed best-performing filters (yearly-low proximity + uptrend
retracement context) rather than either the pattern's bullish theoretical
framing or its raw unfiltered downtrend-only setup.

First "Last Engulfing Bottom" / "Last Engulfing Top" family strategy in
this repo (0 prior index hits for either name) -- distinct from the
already-tested generic Bearish Engulfing (different 2-candle overlap rule:
generic engulfing only requires body containment with no yearly-low or
retracement-context filter) and from Bearish Kicker (2026-09-21,
requires a genuine price GAP between candle 1 and candle 2, whereas Last
Engulfing Bottom explicitly requires body OVERLAP/containment with no gap
condition).

Signal logic (numeric proxy for the source's disclosed identification
guidelines + Three Trading Tidbits refinements)
------------------------------------------------------------------------
1. Uptrend + retracement context (source's own disclosed best setup):
   close well above SMA(uptrend_window) (confirming the larger uptrend),
   AND a short-term pullback into the pattern (close[t-1] below its own
   `retrace_lookback`-day high), rather than a plain primary downtrend.
2. Candle 1 (t-1): bullish (close > open, "white candle").
3. Candle 2 (t): bearish (close < open, "black candle") whose body
   engulfs candle 1's body (open[t] > close[t-1] and close[t] <
   open[t-1], ignoring shadows per source's own instruction).
4. Yearly-low filter (source's own disclosed best-performing subset):
   the pattern's low sits within the bottom `yearly_low_third` fraction
   of the trailing `yearly_window`-day high-low range.
5. Confirmation/entry: short entry on the first subsequent bar whose
   close breaks below the pattern's low (standard breakdown confirmation,
   mirroring the source's own "closes below the bottom of the candlestick
   pattern" Example description).
6. Exit: ATR-based stop (above pattern high) and profit target
   (`target_atr_mult` x ATR below entry), or a max_hold_days time-stop,
   whichever comes first -- same ATR-based short-exit mechanics already
   used successfully in this repo's Bearish Kicker strategy
   (2026-09-21_bearish_kicker_short.py).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({-1,0} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat(
        [(h - l).abs(), (h - prev_c).abs(), (l - prev_c).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def generate_signals(
    price_df: pd.DataFrame,
    uptrend_window: int = 100,
    retrace_lookback: int = 5,
    yearly_window: int = 252,
    yearly_low_third: float = 0.33,
    atr_period: int = 14,
    atr_stop_mult: float = 1.0,
    target_atr_mult: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {-1, 0} short/flat position series for Last Engulfing
    Bottom completions, filtered to the source's disclosed
    best-performing subset (uptrend-retracement context + yearly-low
    proximity)."""
    df = _prep(price_df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    n = len(c)

    sma = c.rolling(uptrend_window).mean()
    uptrend = c.shift(1) > sma.shift(1)
    retrace = c.shift(1) < h.shift(1).rolling(retrace_lookback).max().shift(1)

    candle1_bullish = c.shift(1) > o.shift(1)
    candle2_bearish = c < o
    engulf = (o > c.shift(1)) & (c < o.shift(1))

    roll_high = h.rolling(yearly_window).max()
    roll_low = l.rolling(yearly_window).min()
    pattern_low = l.rolling(2).min()
    yr_range = (roll_high - roll_low).replace(0.0, np.nan)
    pos_in_range = (pattern_low - roll_low) / yr_range
    near_yearly_low = pos_in_range <= yearly_low_third

    pattern_confirm = (
        uptrend.fillna(False)
        & retrace.fillna(False)
        & candle1_bullish.fillna(False)
        & candle2_bearish.fillna(False)
        & engulf.fillna(False)
        & near_yearly_low.fillna(False)
    ).fillna(False)

    pattern_low_val = pattern_low
    pattern_high_val = h.rolling(2).max()

    atr = _atr(df, atr_period)

    position = pd.Series(0, index=c.index, dtype=int)
    in_position = False
    hold_days_left = 0
    stop_price = None
    target_price = None
    pending_breakdown_low = None
    pending_pattern_high = None

    for i in range(n):
        if in_position:
            hit_stop = h.iloc[i] >= stop_price
            hit_target = l.iloc[i] <= target_price
            hold_days_left -= 1
            if hit_stop or hit_target or hold_days_left <= 0:
                in_position = False
                position.iloc[i] = 0
                pending_breakdown_low = None
                continue
            position.iloc[i] = -1
            continue

        if bool(pattern_confirm.iloc[i]):
            pending_breakdown_low = pattern_low_val.iloc[i]
            pending_pattern_high = pattern_high_val.iloc[i]
        elif pending_breakdown_low is not None:
            if c.iloc[i] < pending_breakdown_low:
                entry_price = c.iloc[i]
                entry_atr = atr.iloc[i]
                if pd.notna(entry_atr) and entry_atr > 0:
                    stop_price = max(pending_pattern_high, h.iloc[i]) + atr_stop_mult * entry_atr
                    target_price = entry_price - target_atr_mult * entry_atr
                    in_position = True
                    hold_days_left = max_hold_days
                    position.iloc[i] = -1
                pending_breakdown_low = None
                continue
            # expire stale pending breakdown after a few bars
        position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs). Short
    positions (-1) profit when price falls."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
