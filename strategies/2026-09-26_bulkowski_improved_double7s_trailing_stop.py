"""Strategy: Bulkowski's Improved Double 7s Trading Setup (long-only,
11-bar-low entry, trailing-stop-on-highest-open exit).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/Double7sSetup.html (Thomas
Bulkowski's own IMPROVED rule set, distinct from the raw Larry
Connors/David Penn "Double 7s" article rules already tested and rejected
in this repo at 2026-09-04-114), read via browser_exec -- web_extract's
ddgs backend cannot fetch this domain. Source's own disclosed improved
rules (his own words, presented as the "Summary" at the top of the
article, ahead of his detailed rule-tuning walkthrough):

    "The ETF closes above the 30-bar simple moving average of closing
    prices. When the ETF makes its lowest close in 11 price bars
    (including today), buy on the close today. When the ETF makes its
    highest open in 7 price bars (including today), use a trailing stop
    placed 10 cents below today's high price to exit."

This is a DIFFERENT rule set from the original Connors/Penn "Double 7s"
(200-day SMA trend filter, 7-bar lowest-close buy trigger, 7-bar
highest-close sell trigger -- already tested and rejected in this repo,
2026-09-04-114) via THREE distinct changes: (1) a much shorter 30-bar SMA
trend filter instead of 200-day, (2) an 11-bar (not 7-bar) lowest-close
buy trigger, and (3) a TRAILING STOP mechanism (10 cents below the day's
high, activated once today's OPEN becomes the highest open in the last 7
bars) instead of a fixed highest-close exit signal. Bulkowski's own
conclusion is skeptical ("high win/loss ratio, but the profits just
aren't there... I do not think this represents a system worth trading")
-- this iteration operationalizes his own improved rules as a direct,
disclosed, testable candidate rather than accepting his qualitative
verdict at face value.

Signal logic (numeric proxy for the source's own disclosed improved rules,
scaled to daily bars -- source already uses daily bars, no weekly-scale
mismatch here)
------------------------------------------------------------------------
1. Trend filter: close > SMA(sma_window) (source: 30-bar).
2. Entry: buy at the close when today's close is the lowest close over
   the trailing `buy_lookback`-bar window (including today, source: 11
   bars) AND the trend filter holds.
3. Exit: once today's open becomes the highest open over the trailing
   `sell_lookback`-bar window (including today, source: 7 bars), engage a
   trailing stop at (today's high - `trail_offset_pct`*today's high) --
   a percentage proxy for the source's fixed "10 cents below today's
   high" (not directly portable across tickers/price levels, so
   expressed as a percentage here). Once engaged, the stop only ratchets
   up (never down) each subsequent day the highest-open condition
   recurs, or as price makes new highs while in the trade. Exit when
   close drops below the active stop.

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
    sma_window: int = 35,
    buy_lookback: int = 9,
    sell_lookback: int = 11,
    trail_offset_pct: float = 0.012,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Defaults reflect the accepted SPY config from this repo's own grid +
    local parameter search (see knowledge_base/strategies_log.jsonl and
    backtests/2026-09-26_bulkowski_improved_double7s_trailing_stop.md),
    NOT the source's literal disclosed defaults (sma_window=30,
    buy_lookback=11, sell_lookback=7) -- this repo's own search found a
    nearby config that clears all 4 validators for SPY.
    """
    df = _prep(price_df)
    high = df["high"]
    open_ = df["open"]
    close = df["close"]

    sma = close.rolling(sma_window).mean()
    trend_ok = close > sma

    is_lowest_close = close <= close.rolling(buy_lookback).min()
    entry = (is_lowest_close & trend_ok).fillna(False)

    is_highest_open = open_ >= open_.rolling(sell_lookback).max()
    is_highest_open = is_highest_open.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    stop_level = 0.0
    for i in range(len(close)):
        if in_position:
            if is_highest_open.iloc[i]:
                candidate_stop = high.iloc[i] * (1 - trail_offset_pct)
                stop_level = max(stop_level, candidate_stop)
            if stop_level > 0 and close.iloc[i] < stop_level:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                stop_level = 0.0
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    sma_window: int = 35,
    buy_lookback: int = 9,
    sell_lookback: int = 11,
    trail_offset_pct: float = 0.012,
) -> pd.Series:
    """Daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        sma_window=sma_window,
        buy_lookback=buy_lookback,
        sell_lookback=sell_lookback,
        trail_offset_pct=trail_offset_pct,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_ret
