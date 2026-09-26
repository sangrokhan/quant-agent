"""Strategy: Bulkowski Rectangle Bottom Setup (long-only breakout, 3-day-or-5pct exit).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/RectangleBottomSetup.html (Thomas
Bulkowski, read via browser_exec -- web_extract's ddgs backend cannot fetch
this domain). Source's own disclosed out-of-sample test (~1550 stocks,
mid-1991 to June 2010, 261 trades, $10 commission each way):

    "The best performing trading setup begins with price rising above the
    rectangle bottom. Sell at the close three trading days later or if
    profits reaches or exceeds 5%. No stop is used. The average trade
    using this setup makes about 2.5% in 5 calendar days, wins 73% of the
    time, and has a win/loss ratio of 4.83."

This is DISTINCT from the already-tested-and-rejected 2026-09-24-104
Rectangle Bottom entry (source: thepatternsite.com/rectbots.html, the
general chart-pattern-encyclopedia page), which used a measured-move
price target and a downtrend-entry-context filter. This strategy uses
Bulkowski's OWN rank-1 TRADING-SETUP-SPECIFIC exit rule instead: a pure
"3 trading days OR 5% profit, whichever comes first, no stop" exit -- the
best-ranked rule from a dedicated 24-variant setup test, with NO trend
filter (unlike the setup's rank-2/3 variants which add SMA filters).
First "3-day-or-N%-profit" combined exit rule in this repo (all prior
fixed-holding-period strategies use either a pure time-stop OR a pure
profit-target, never Bulkowski's specific "whichever comes first" combo).

Signal logic (numeric proxy for the source's qualitative rectangle-bottom
detection + its own disclosed rank-1 rule)
------------------------------------------------------------------------
1. Rectangle-bottom detection: over a trailing `range_window`-day window
   (ending the day before today, to avoid look-ahead), classify the
   period as a "rectangle" if (rolling_high - rolling_low)/rolling_low <=
   `max_range_pct` (source: "price bounces up and down, touching two
   horizontal or nearly horizontal trendlines").
2. Breakout / entry: on the first bar where (a) the rectangle condition
   held over the prior window, and (b) today's close exceeds that prior
   window's rolling high (source: "buy stop a penny above the top of the
   formation", approximated at the close) -> go long. NO SMA/trend filter
   (source's rank-1 "3 day or 5% exit, no stop" variant uses no trend
   filter at all -- distinct from the already-accepted Rectangle Top
   Setup, 2026-09-26-001, which DOES require an SMA filter as its
   rank-1 rule).
3. Exit: close the position at the EARLIER of (a) `hold_days` trading
   days after entry, or (b) cumulative return since entry reaching
   `profit_target_pct` (source's own disclosed "3 day or 5% exit, no
   stop" rank-1 rule).
4. No overlapping positions: while in a trade, ignore new breakout
   signals until the current position closes.

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
    range_window: int = 15,
    max_range_pct: float = 0.08,
    hold_days: int = 3,
    profit_target_pct: float = 0.05,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    range_window: lookback (days) over which we check for a tight
        horizontal "rectangle" channel (Bulkowski's rectangle bottom).
    max_range_pct: max allowed (rolling_high - rolling_low) / rolling_low
        over range_window for the period to qualify as a rectangle.
    hold_days: max holding period in trading days (source's "3 day"
        rank-1 rule).
    profit_target_pct: early-exit profit target (source's "or 5%" rank-1
        rule) -- exit as soon as cumulative return since entry reaches
        this level, even before hold_days elapses.
    """
    df = _prep(price_df)
    close = df["close"]

    rolling_high = close.rolling(range_window).max()
    rolling_low = close.rolling(range_window).min()
    range_pct = (rolling_high - rolling_low) / rolling_low

    is_rectangle_prior = (range_pct <= max_range_pct).shift(1).fillna(False)
    rect_top_prior = rolling_high.shift(1)

    breakout = (is_rectangle_prior & (close > rect_top_prior)).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_price = 0.0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            cum_ret = (close.iloc[i] / entry_price) - 1.0
            if held >= hold_days or cum_ret >= profit_target_pct:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(breakout.iloc[i]):
                in_position = True
                entry_idx = i
                entry_price = close.iloc[i]
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    range_window: int = 15,
    max_range_pct: float = 0.08,
    hold_days: int = 3,
    profit_target_pct: float = 0.05,
) -> pd.Series:
    """Daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        range_window=range_window,
        max_range_pct=max_range_pct,
        hold_days=hold_days,
        profit_target_pct=profit_target_pct,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_ret
