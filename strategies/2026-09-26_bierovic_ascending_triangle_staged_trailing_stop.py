"""Strategy: Bulkowski/Bierovic Ascending Triangle Setup (long-only breakout,
staged trailing-stop exit).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/BierovicSetup.html (Thomas
Bulkowski discussing Thomas Bierovic's Sept 2002 Active Trader article
"The ups and downs of triangles"), read via browser_exec -- web_extract's
ddgs backend cannot fetch this domain. Source's own disclosed rules and
1991-2011 test (627 stocks, 1061 ascending-triangle trades):

    "The top of the triangle must be above the 13-day and 55-day EMAs.
    The start of the triangle to the day before breakout must be at least
    15 price bars. Place a buy stop ten cents above the top trendline and
    buy providing the buy price is also above both EMAs. Set an initial
    stop a dime below the low the day before the breakout. Raise the
    stop to break even after a close above the top of the triangle plus
    50% of its height. After a new highest close since entry, raise the
    stop to below the most recent swing low. After price reaches the top
    of the triangle plus its height, place a trailing stop ten cents
    below the prior bar's low."

Source's own result: avg gain only 0.8%/trade for trades meeting all
entry filters (vs 1.7%/trade for the trades the filters EXCLUDED), 21.1%
max drawdown, 60% win/loss ratio, 15-day avg hold -- source itself
concludes "the entry rules do more harm than good" (the EMA-above filters
and 15-bar minimum-length filter systematically excluded the MORE
profitable triangles). This iteration tests both the WITH-filter and
WITHOUT-filter (`require_ema_filter=False`) variants, directly
operationalizing the source's own finding as a testable parameter rather
than assuming the filtered version is better.

This is distinct from the already-rejected 2026-09-08-112 Ascending
Triangle entry (trendline-OLS-fit detection + measured-move target +
fixed stop) via its DIFFERENT detection method (rolling-high flat-top +
rolling-low rising-trend proxy, no OLS fit) and its unique STAGED
TRAILING-STOP exit mechanic (breakeven -> swing-low trail -> profit-
target trail), which no prior chart-pattern strategy in this repo uses.

Signal logic (numeric proxy for the source's qualitative triangle
detection + its own disclosed multi-stage stop rules)
------------------------------------------------------------------------
1. Ascending-triangle detection: over a trailing `pattern_window`-day
   window (>= 15 bars per source), classify as an ascending triangle if
   (a) the rolling HIGH is roughly flat ((rolling_high - rolling_high at
   window start)/rolling_high <= `flat_top_tol`), and (b) the rolling LOW
   is rising (low at window end > low at window start * (1 +
   `min_rise_pct`)) -- a flat resistance with rising support.
2. Entry: close breaks above the prior window's flat top (a proxy for
   "buy stop ten cents above the top trendline"), optionally gated by
   close > EMA(13) AND close > EMA(55) (source's own entry filter,
   `require_ema_filter` parameter tests both variants per source's own
   finding).
3. Exit (staged trailing stop, applied via next-bar low/close checks):
   - Initial stop: the low of the bar before breakout.
   - Once cumulative gain since entry >= 50% of triangle height (pattern
     top - pattern-window low): raise stop to breakeven (entry price).
   - Once cumulative gain since entry >= 100% of triangle height: switch
     to a trailing stop at the prior bar's low (source's final stage).
   - Exit when close drops below the currently active stop level.

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
    pattern_window: int = 15,
    flat_top_tol: float = 0.03,
    min_rise_pct: float = 0.03,
    ema_fast: int = 13,
    ema_slow: int = 55,
    require_ema_filter: bool = True,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    rolling_high = high.rolling(pattern_window).max()
    # flat-top proxy: the window's overall high vs. the high seen in just its
    # FIRST HALF should be close together (a flat top, not a rising one) --
    # comparing the full-window high to the first-half-window high avoids
    # anchoring on a single noisy bar.
    half_window = max(pattern_window // 2, 3)
    high_first_half = high.rolling(half_window).max().shift(pattern_window - half_window)
    flat_top = ((rolling_high - high_first_half).abs() / rolling_high) <= flat_top_tol

    # rising-low proxy: min low of the window's second half should sit
    # meaningfully above the min low of its first half (support rising).
    low_first_half_min = low.rolling(half_window).min().shift(pattern_window - half_window)
    low_second_half_min = low.rolling(half_window).min()
    rising_low = low_second_half_min > low_first_half_min * (1 + min_rise_pct)

    is_triangle_prior = (flat_top & rising_low).shift(1).fillna(False)
    triangle_top_prior = rolling_high.shift(1)
    triangle_low_prior = low.rolling(pattern_window).min().shift(1)
    triangle_height_prior = (triangle_top_prior - triangle_low_prior).clip(lower=1e-9)

    ema13 = close.ewm(span=ema_fast, adjust=False).mean()
    ema55 = close.ewm(span=ema_slow, adjust=False).mean()
    ema_ok = (close > ema13) & (close > ema55) if require_ema_filter else pd.Series(True, index=close.index)

    breakout = (is_triangle_prior & (close > triangle_top_prior) & ema_ok).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_price = 0.0
    triangle_height = 0.0
    triangle_top = 0.0
    stop_level = 0.0
    stage = 0  # 0=initial, 1=breakeven, 2=trailing

    for i in range(len(close)):
        if in_position:
            gain = close.iloc[i] - entry_price
            if stage < 1 and gain >= 0.5 * triangle_height:
                stage = 1
                stop_level = max(stop_level, entry_price)
            if stage < 2 and gain >= triangle_height:
                stage = 2
            if stage == 2:
                stop_level = max(stop_level, low.iloc[i - 1] if i > 0 else stop_level)

            if close.iloc[i] < stop_level:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(breakout.iloc[i]):
                in_position = True
                entry_price = close.iloc[i]
                triangle_height = triangle_height_prior.iloc[i]
                triangle_top = triangle_top_prior.iloc[i]
                stop_level = low.iloc[i - 1] if i > 0 else close.iloc[i] * 0.95
                stage = 0
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    pattern_window: int = 15,
    flat_top_tol: float = 0.03,
    min_rise_pct: float = 0.03,
    ema_fast: int = 13,
    ema_slow: int = 55,
    require_ema_filter: bool = True,
) -> pd.Series:
    """Daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        pattern_window=pattern_window,
        flat_top_tol=flat_top_tol,
        min_rise_pct=min_rise_pct,
        ema_fast=ema_fast,
        ema_slow=ema_slow,
        require_ema_filter=require_ema_filter,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_ret
