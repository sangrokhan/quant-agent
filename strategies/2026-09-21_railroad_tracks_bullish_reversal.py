"""Strategy: Bullish Railroad Tracks candlestick reversal pattern.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Per multiple corroborating trading-education sources (TradingView's "Railway
Tracks Pattern Trading Strategy" writeup and Google's AI-overview synthesis
of the pattern's standard definition, both read this iteration), the
"Railroad Tracks" (a.k.a. "Railway Tracks") pattern is a 2-candle reversal
setup: two consecutive candles with long, roughly-equal-length real bodies
(each real body covering at least `min_body_ratio` of that candle's total
high-low range) of OPPOSITE colors -- forming a "==" shape reminiscent of
parallel rail tracks. The BULLISH variant appears at a downtrend bottom:
bar1 is a long bearish candle, bar2 is a long bullish candle of similar
length, opening near bar1's close and closing back up near bar1's open.
Sources' own trading rule: enter long above bar2's high (breakout
confirmation), place a stop below bar2's low, target a fixed R-multiple.

This is a genuinely new pattern for this repo (0 prior "railroad
tracks"/"railway tracks" hits in strategies_index.jsonl) -- distinct from
Bullish Engulfing (single dominant candle, no "equal length" requirement),
Piercing Pattern (requires bar2 to close ABOVE bar1's body midpoint but not
necessarily match bar1's length), and Harami (bar2 INSIDE bar1's body,
opposite containment relationship).

Signal logic
------------
- Downtrend filter: close[t-2] < close[t-2 - trend_lookback] (require the
  pattern to appear after a real downtrend, per every source's stated
  context requirement).
- Bar1 (t-1) is a long bearish candle: close[t-1] < open[t-1], and its real
  body covers >= min_body_ratio of its own high-low range.
- Bar2 (t) is a long bullish candle: close[t] > open[t], real body also
  covers >= min_body_ratio of its own high-low range.
- "Parallel tracks" equal-length requirement: the two real bodies' lengths
  are within length_tolerance of each other (relative to the larger body).
- Entry: long at the close of the bar that breaks above bar2's own high
  within `confirm_window` bars after the pattern (source's own "buy-stop
  above bar2's high" breakout-confirmation rule, adapted to close-based
  daily bars since we have no intrabar stop-order execution here).
- Exit: close falls below bar2's own low (source's stop-loss reference
  level) OR max_hold_days reached, whichever comes first.

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


def generate_signals(
    price_df: pd.DataFrame,
    trend_lookback: int = 10,
    min_body_ratio: float = 0.7,
    length_tolerance: float = 0.35,
    confirm_window: int = 3,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    idx = df.index
    n = len(idx)

    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]

    rng = (high - low).replace(0.0, float("nan"))
    body = (close - open_).abs()
    body_ratio = body / rng

    prior_close_shift = close.shift(2)
    downtrend = prior_close_shift < prior_close_shift.shift(trend_lookback)

    bar1_bearish = close.shift(2) < open_.shift(2)
    bar1_long_body = body_ratio.shift(2) >= min_body_ratio
    bar2_bullish = close.shift(1) > open_.shift(1)
    bar2_long_body = body_ratio.shift(1) >= min_body_ratio

    bar1_body_len = body.shift(2)
    bar2_body_len = body.shift(1)
    max_body = pd.concat([bar1_body_len, bar2_body_len], axis=1).max(axis=1)
    body_len_diff = (bar1_body_len - bar2_body_len).abs()
    equal_length = (body_len_diff / max_body) <= length_tolerance

    pattern_confirmed_2bars_ago = (
        downtrend.fillna(False)
        & bar1_bearish.fillna(False)
        & bar1_long_body.fillna(False)
        & bar2_bullish.fillna(False)
        & bar2_long_body.fillna(False)
        & equal_length.fillna(False)
    )
    # pattern_confirmed_2bars_ago[t] tells us bars (t-2, t-1) formed the
    # pattern as of bar t's open; bar2's own high/low are at index t-1.
    bar2_high = high.shift(1)
    bar2_low = low.shift(1)

    position = pd.Series(0, index=idx, dtype=int)
    in_position = False
    entry_i = -1
    pending_pattern_i = -1  # index i where pattern_confirmed_2bars_ago is True (bar2 = i-1)

    for i in range(n):
        if in_position:
            held = i - entry_i
            stop_hit = close.iloc[i] < bar2_low.iloc[entry_i] if entry_i >= 0 else False
            if stop_hit or held >= max_hold_days:
                in_position = False
            else:
                position.iloc[i] = 1
            continue

        if bool(pattern_confirmed_2bars_ago.iloc[i]):
            pending_pattern_i = i

        if pending_pattern_i >= 0 and (i - pending_pattern_i) <= confirm_window:
            ref_high = bar2_high.iloc[pending_pattern_i]
            if pd.notna(ref_high) and close.iloc[i] > ref_high:
                in_position = True
                entry_i = i
                position.iloc[i] = 1
                pending_pattern_i = -1
        elif pending_pattern_i >= 0 and (i - pending_pattern_i) > confirm_window:
            pending_pattern_i = -1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_lookback: int = 10,
    min_body_ratio: float = 0.7,
    length_tolerance: float = 0.35,
    confirm_window: int = 3,
    max_hold_days: int = 10,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        trend_lookback=trend_lookback,
        min_body_ratio=min_body_ratio,
        length_tolerance=length_tolerance,
        confirm_window=confirm_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    # Position at t determines exposure during the return realized from t-1
    # to t is inconsistent with lookahead; shift position by 1 to only earn
    # the NEXT day's return after a signal is confirmed at close of day t.
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
