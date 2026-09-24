"""Strategy: Bulkowski "Above the Stomach" candlestick, bullish reversal (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/AboveStomach.html (Thomas Bulkowski,
browser_exec fallback -- web_search's DDGS backend returns unrelated results
for this domain, confirmed again this iteration).

Source's own disclosed identification rules and statistics:
    "Look for two candles in a downward price trend. The first candle is
    black and the second white. The body of the second should be at or
    above the middle of the first candle's body."
    Theoretical performance: Bullish reversal. Tested performance: Bullish
    reversal 66% of the time. Frequency rank: 32/103. Overall performance
    rank: 31/103. Source's own "Three Trading Tidbits": "Above the stomach
    works best as part of a downward retracement in an upward price trend"
    (page 93) -- i.e. the source's own strongest disclosed context is NOT
    a standalone downtrend reversal but a pullback-in-uptrend continuation
    setup. This strategy implements exactly that stronger, source-preferred
    variant: require a LONGER-TERM uptrend (close > SMA(uptrend_window))
    while the two-candle pattern itself forms during a short-term downward
    retracement (close[t-1] < close[t-1-retrace_lookback]), matching the
    source's own highest-conviction disclosed use case rather than the
    generic (weaker, 66%-only) standalone-downtrend version.

First "Above the Stomach" / "Below the Stomach" family strategy in this
repo (0 prior index hits for either name) -- distinct from every other
2-candle containment/overlap pattern already tested (Homing Pigeon requires
full containment; Harami requires full containment; Stick Sandwich requires
3 bars; Meeting Lines requires equal closes) via its specific "second body
at/above first body's midpoint" numeric overlap rule with no containment
requirement.

Signal logic
------------
1. Longer-term uptrend filter: close > SMA(uptrend_window) (source's own
   preferred context: "downward retracement in an upward price trend").
2. Short-term retracement filter: close[t-1] < close[t-1-retrace_lookback]
   (a genuine local pullback leading into the pattern).
3. Bar1 (t-1) bearish (black): close[t-1] < open[t-1].
4. Bar2 (t) bullish (white): close[t] > open[t].
5. Overlap rule (source's own numeric criterion): bar2's body midpoint
   ((open[t]+close[t])/2) is at or above bar1's body midpoint
   ((open[t-1]+close[t-1])/2).
6. Entry: at bar2's own close once the pattern confirms (same
   confirmed-at-close convention as this repo's other candlestick
   strategies, e.g. Homing Pigeon 2026-09-21).
7. Exit: close falls below its own SMA(exit_sma_window) (retracement/
   trend-continuation failure) OR a max_hold_days time-stop, whichever
   comes first -- same exit convention as this repo's other
   single-pattern-trigger candlestick strategies.

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
    uptrend_window: int = 100,
    retrace_lookback: int = 5,
    exit_sma_window: int = 10,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    idx = df.index
    n = len(idx)

    open_ = df["open"]
    close = df["close"]

    uptrend_sma = close.rolling(uptrend_window).mean()
    uptrend_filter = close > uptrend_sma
    retrace_filter = close.shift(1) < close.shift(1 + retrace_lookback)

    bar1_bearish = close.shift(1) < open_.shift(1)
    bar2_bullish = close > open_

    bar1_mid = (open_.shift(1) + close.shift(1)) / 2.0
    bar2_mid = (open_ + close) / 2.0
    overlap_rule = bar2_mid >= bar1_mid

    pattern_confirmed = (
        uptrend_filter.fillna(False)
        & retrace_filter.fillna(False)
        & bar1_bearish.fillna(False)
        & bar2_bullish.fillna(False)
        & overlap_rule.fillna(False)
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
