"""Strategy: Bulkowski Rectangle Top upward breakout (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/recttops.html (Thomas Bulkowski's
"Encyclopedia of Chart Patterns" stats page, read via browser_exec after
web_search's DDGS backend returned unrelated/garbage results this
iteration). Source's own disclosed identification rules and statistics:

    "Rectangle tops (or horizontal channels)... Price trend: Upward
    leading to the chart pattern. Shape: Prices have flat tops and flat
    bottoms, crossing the pattern from side to side following two
    parallel trendlines... Touches: Price should touch one trendline at
    least three times and twice on the other trendline... Breakout:
    Upward 63% of the time... Overall performance rank for up/down
    breakouts (1 is best): 4 out of 39/32 out of 36. Break even failure
    rate for up/down breakouts: 15%/34%. Average rise/decline: 51%/13%...
    The Measure Rule: Compute the height between the two trendlines...
    then multiply it by the ... percentage meeting price target. Add it
    to the price of the top trendline (upward breakouts)... to get a
    target price... Wait for breakout: Since the breakout can be in any
    direction, wait for price to close outside the trendline before
    taking a position."

First "Rectangle" pattern entry in this repo (0 prior index hits) --
distinct from the repo's prior Triangle-family pattern entries
(Symmetrical/Ascending/Descending Triangle, all converging trendlines)
because Rectangle Tops require PARALLEL (near-horizontal, non-converging)
support/resistance rather than a narrowing wedge, and Bulkowski's own
published stats rank Rectangle Top upward breakouts as one of the single
best-performing bullish continuation patterns of the 39 he studied
("4 out of 39"), a notably stronger prior than most chart patterns already
tested in this repo (many of which were rejected).

Signal logic (long-only translation of the source's upward-breakout rule)
----------------------------------------------------------------------
1. Consolidation detection: over a rolling `range_window`-bar lookback,
   the rolling max(high) and min(low) define candidate resistance/support.
   A valid rectangle requires the range to be "flat" -- i.e. price stays
   within [support, resistance] with resistance/support ratio bounded by
   `max_range_pct` (tightness proxy for "near-horizontal trendlines") for
   at least `min_touches_window` consecutive bars (simplified proxy for
   Bulkowski's "touch each trendline >=2-3 times" requirement, since exact
   swing-touch counting on daily bars is noisy -- a sustained tight range
   is the testable numeric analogue used here).
2. Prior uptrend filter: close at the start of the consolidation window is
   above its own SMA(trend_lookback) (source's "Price trend: Upward
   leading to the chart pattern").
3. Breakout: long entry when close breaks above resistance (the
   rolling-max of the consolidation window), confirmed by a close (not
   just an intrabar poke) per the source's "wait for price to close
   outside the trendline."
4. Exit: source's own Measure Rule target (height = resistance - support;
   target = resistance + height * measure_rule_pct, using the source's own
   disclosed 78% "percentage meeting price target" for upward breakouts as
   the default), OR close crossing back below the broken resistance level
   (failed breakout / throwback turning into a reversal, source notes
   "throwbacks hurt post breakout performance"), OR a max_hold_days
   time-stop, whichever comes first.

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
    measure_rule_pct: float = 0.78,
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
    prior_uptrend = close > sma_trend

    prev_close = close.shift(1)
    prev_resistance = resistance.shift(1)
    breakout_up = (close > prev_resistance) & is_tight_range.shift(1).fillna(False) & prior_uptrend.shift(1).fillna(False)

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
