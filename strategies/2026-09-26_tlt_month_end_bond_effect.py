"""Strategy: TLT Month-End Bond Effect (calendar seasonality, long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://algocloud.com/the-month-end-bond-effect-a-high-probability-tlt-seasonal-strategy/
(read via browser_exec -- web_extract's ddgs backend cannot fetch this
domain), corroborated by QuantifiedStrategies.com's own (paywalled) "TLT
Long-Term Treasuries Calendar Effects" finding that "the first seven
trading days of the month produce strong negative returns, while the rest
of the month has doubled the returns of buying and holding TLT."
AlgoCloud's own disclosed fully-mechanical rule:

    "Entry Condition: Enter at the end of the day when the day of the
    month is greater than or equal to 15. If the 15th falls on a weekend,
    the system automatically triggers on the next available trading day.
    Exit Condition: Hold the position until the first trading day of the
    new month. Once the new month begins, the system closes the
    position."

Source's own claimed backtest result: max drawdown 12%, "low volatility",
consistent capture of month-end momentum (source explicitly notes the
backtest shown EXCLUDES transaction costs, and part of TLT's total return
in this window may be dividend-timing-related since TLT's ex-dividend date
typically falls on the first business day of the month with payouts 5-7
days later -- both caveats are tested honestly here via this repo's own
transaction-cost validator, though dividend effects are not separately
decomposed since this repo's price series is presumed adjusted-close per
data/loaders.py convention).

First TLT-specific calendar/seasonality strategy in this repo (0 prior
"TLT seasonal"/"month-end bond effect" hits) -- distinct from all prior
turn-of-month equity strategies (which trade SPY/QQQ, not TLT, and use a
different day-of-month window) and from all prior SPY/TLT cross-asset
ratio strategies (which trade the RATIO, never TLT held outright on its
own calendar cycle).

Signal logic (direct implementation of the source's disclosed rule, no
approximation needed -- this is a pure calendar rule, not a chart pattern)
------------------------------------------------------------------------
1. Long from the close of the first trading day on/after the `entry_dom`
   calendar day-of-month (source: 15) through the last trading day of
   that calendar month.
2. Flat otherwise (i.e. flat during the first `entry_dom`-1 calendar days
   of each month).
3. No stop-loss, no profit target -- a pure calendar-timing rule per the
   source's own description.

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
    entry_dom: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long from the first trading day whose calendar day-of-month >=
    `entry_dom` through the last trading day of that same month; flat for
    the rest of the month.
    """
    df = _prep(price_df)
    idx = df.index

    position = pd.Series(0, index=idx, dtype=int)
    for i in range(len(idx)):
        d = idx[i]
        if d.day >= entry_dom:
            position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    entry_dom: int = 15,
) -> pd.Series:
    """Daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(price_df, entry_dom=entry_dom)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_ret
