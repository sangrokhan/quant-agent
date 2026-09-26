"""Strategy: Bulkowski Rectangle Top Setup (long-only breakout, fixed 3-day exit).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/RectangleTopSetup.html (Thomas
Bulkowski, read via browser_exec -- web_extract's ddgs backend cannot fetch
this domain). Source's own disclosed out-of-sample test (~1550 stocks,
mid-1991 to June 2010, 599 trades, $10 commission each way):

    "Set a buy stop a penny above the top of a rectangle top chart pattern
    and above a 21-day simple moving average. When price breaks out of the
    chart pattern, the stop should get you in. Sell at the close three
    trading days later. The setup makes, on average, over 3% in 5 calendar
    days with a win/loss ratio of over 7."

Source's rank-1 (best) tested variant: "Buy price >21 day SMA, 3 day exit"
-- avg $309.66/trade (3.1%), 75% win rate, W/L ratio 7.13, 599 trades, max
drawdown 28%. This is a fixed-holding-period breakout strategy, distinct
from every other chart-pattern breakout already tested in this repo (all
of which use a measured-move price target and/or a trend-break exit,
never Bulkowski's own explicit "N trading days regardless of price"
holding-period rule) -- first fixed-N-day-holding-period breakout
strategy in this repo.

Signal logic (numeric proxy for the source's qualitative rectangle-top
detection + its own disclosed best-ranked rule)
------------------------------------------------------------------------
1. Rectangle-top detection: over a trailing `range_window`-day window, the
   period is classified as a "rectangle" if (rolling_high - rolling_low) /
   rolling_low <= `max_range_pct` (a tight horizontal channel, source's
   "bounces between two horizontal or nearly horizontal trendlines").
2. Breakout / entry: on the first bar where (a) the rectangle condition
   held over the prior `range_window` days (using the window ENDING the
   day before, to avoid look-ahead), (b) today's close exceeds that prior
   window's rolling high (the "penny above the top" breakout, approximated
   at the close), and (c) today's close is above its own `sma_window`-day
   SMA (source's own best-ranked "Buy price >21 day SMA" filter) -> go
   long.
3. Exit: unconditionally close the position `hold_days` trading days after
   entry (source's own disclosed "sell at the close N trading days
   later" rule, no price-based stop or target in the source's rank-1
   variant) -- a pure fixed-holding-period exit, not a stop/target/trend
   exit like every other breakout strategy already in this repo.
4. No overlapping positions: while in a trade, ignore new breakout
   signals until the current position closes (source trades one rectangle
   at a time).

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
    sma_window: int = 21,
    hold_days: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    range_window: lookback (days) over which we check for a tight
        horizontal "rectangle" channel (Bulkowski's rectangle top).
    max_range_pct: max allowed (rolling_high - rolling_low) / rolling_low
        over range_window for the period to qualify as a rectangle.
    sma_window: SMA period for the source's best-ranked trend filter
        ("Buy price >21 day SMA").
    hold_days: fixed holding period in trading days (source's own
        disclosed "3 day exit" rank-1 rule).
    """
    df = _prep(price_df)
    close = df["close"]

    rolling_high = close.rolling(range_window).max()
    rolling_low = close.rolling(range_window).min()
    range_pct = (rolling_high - rolling_low) / rolling_low

    # Shift by 1 so the "rectangle" and its top/SMA are measured using data
    # available BEFORE today's bar -- avoids using today's own close to
    # define the very channel today's close is being tested against.
    is_rectangle_prior = (range_pct <= max_range_pct).shift(1).fillna(False)
    rect_top_prior = rolling_high.shift(1)
    sma = close.rolling(sma_window).mean()

    breakout = (
        is_rectangle_prior
        & (close > rect_top_prior)
        & (close > sma)
    ).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(breakout.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    range_window: int = 15,
    max_range_pct: float = 0.08,
    sma_window: int = 21,
    hold_days: int = 3,
) -> pd.Series:
    """Daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        range_window=range_window,
        max_range_pct=max_range_pct,
        sma_window=sma_window,
        hold_days=hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_ret
