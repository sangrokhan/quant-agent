"""Strategy: Bulkowski Rectangle Bottom upward breakout (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/rectbots.html (Thomas Bulkowski's
"Encyclopedia of Chart Patterns" stats page; read via browser_exec after
web_search's DDGS backend returned unrelated/garbage results this
iteration). Source's own disclosed statistics and identification rules:

    "Rectangle bottoms, so called because price enters the pattern from
    the top, are good performing chart patterns. The performance rank is
    near the top of the list. ... Overall performance rank for up/down
    breakouts (1 is best): 8 out of 39/14 out of 36. Break even failure
    rate for up/down breakouts: 15%/24%. Average rise/decline: 48%/16%.
    ... Price trend: Downward leading to the chart pattern. Shape: Prices
    have flat tops and flat bottoms, crossing the pattern from side to
    side following two parallel trendlines... Touches: Price should touch
    one trendline at least three times and the other trendline twice
    (5-touch minimum)... Breakout: Upward 59% of the time. ... Wait for
    breakout: Since the breakout can be in any direction, wait for price
    to close outside the trendline before taking a position. ... Yearly
    low: Rectangles with breakouts (up or down) near the yearly low
    perform best."

This repo already tested and accepted the closely-related Rectangle Top
pattern this cron trigger (2026-09-24-099, QQQ accepted) -- Bulkowski
explicitly distinguishes the two by PRIOR TREND CONTEXT: Rectangle Top
enters the consolidation from an uptrend ("price enters the pattern from
the bottom"), Rectangle Bottom enters from a DOWNTREND ("price enters the
pattern from the top"). Both share the same parallel-trendline
consolidation shape and Measure Rule mechanics, but the differing prior
trend context and Bulkowski's own separately-tracked statistics (rank
8/39 vs 4/39, break-even failure 15% for both but distinct average
rise/decline profiles) make this a genuinely distinct, separately
testable hypothesis in Bulkowski's own taxonomy, not a duplicate.

Signal logic (identical mechanical shape to Rectangle Top, opposite prior
trend filter)
----------------------------------------------------------------------
1. Consolidation detection: identical tight-range detector to this repo's
   already-tested Rectangle Top strategy (rolling range_window, max_range_pct
   tightness threshold).
2. Prior DOWNTREND filter (the key distinguishing rule vs. Rectangle Top):
   close at the start of the consolidation window is BELOW its own
   SMA(trend_lookback) (source: "Price trend: Downward leading to the
   chart pattern").
3. Breakout: long entry when close breaks above resistance (rolling-max
   of the consolidation window), confirmed by a close, per source's "wait
   for price to close outside the trendline."
4. Exit: source's own Measure Rule target (height = resistance - support;
   target = resistance + height * measure_rule_pct, using the source's
   own disclosed 79% "percentage meeting price target" for upward
   breakouts -- notably higher than Rectangle Top's 78%), OR close
   crossing back below the broken resistance (failed breakout), OR a
   max_hold_days time-stop, whichever comes first.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
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


def generate_signals(
    price_df: pd.DataFrame,
    range_window: int = 20,
    max_range_pct: float = 0.08,
    trend_lookback: int = 50,
    measure_rule_pct: float = 0.79,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    n = len(close)

    resistance = high.rolling(range_window).max()
    support = low.rolling(range_window).min()
    range_pct = (resistance - support) / support.replace(0.0, np.nan)
    is_tight_range = range_pct <= max_range_pct

    sma_trend = close.rolling(trend_lookback).mean()
    prior_downtrend = close < sma_trend

    prev_resistance = resistance.shift(1)
    breakout_up = (
        (close > prev_resistance)
        & is_tight_range.shift(1).fillna(False)
        & prior_downtrend.shift(1).fillna(False)
    )

    entries = breakout_up.fillna(False).to_numpy()
    resistance_arr = resistance.to_numpy()
    support_arr = support.to_numpy()
    close_arr = close.to_numpy()

    position = np.zeros(n, dtype=int)
    in_pos = False
    entry_bar = -1
    entry_resistance = np.nan
    target_price = np.nan

    for t in range(n):
        if entries[t] and not in_pos:
            in_pos = True
            entry_bar = t
            entry_resistance = resistance_arr[t - 1] if t > 0 else resistance_arr[t]
            height = entry_resistance - support_arr[t - 1] if t > 0 else np.nan
            target_price = entry_resistance + height * measure_rule_pct if not np.isnan(height) else np.inf
        if in_pos:
            position[t] = 1
            held = t - entry_bar
            failed_breakout = close_arr[t] < entry_resistance
            hit_target = not np.isnan(target_price) and close_arr[t] >= target_price
            if failed_breakout or hit_target or held >= max_hold_days:
                in_pos = False

    return pd.Series(position, index=close.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
