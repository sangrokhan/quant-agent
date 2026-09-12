"""Strategy: September-avoidance calendar seasonality filter, long-only.

Hypothesis (see knowledge_base id 2026-09-12-170):
Per QuantifiedStrategies.com's "September Is The Worst Month For Stocks"
(https://www.quantifiedstrategies.com/september-is-the-worst-month-for-stocks/),
a month-by-month S&P 500 close-to-close study (1970-2019, price only, no
dividends) found September to be decisively the worst calendar month by
both average gain (-0.58%, the ONLY negative average of all 12 months) and
win-ratio (46%, also the lowest of all 12 months) -- every other month
averaged a positive gain with a >=49% win-ratio. This strategy directly
operationalizes the source's own disclosed monthly statistics table as a
calendar-based regime filter: stay OUT of the market only during the one
month the source's own data shows a negative expectancy, remain invested
every other month.

First pure month-of-year calendar-avoidance strategy in this repo, distinct
from Turn-of-Month / Halloween-Indicator (Nov-Apr vs May-Oct) / January
Effect / Santa Claus Rally (all already tested multi-month or specific-week
constructs) -- this is a single-month EXCLUSION filter based on the
source's own worst-single-month finding, applied as a long-only base
strategy (not a gate layered on top of a separate technical signal).

Signal logic
------------
- Long (position=1) in every calendar month NOT in `avoid_months`
  (default: September only, per the source's own single worst-month
  finding).
- Flat (position=0) during any month in `avoid_months`.
- Optional `trend_window`: if > 0, additionally require close above its
  own `trend_window`-day SMA to stay long even in non-avoided months (a
  standard robustness check on top of the raw calendar effect; set to 0
  to test the pure unconditional calendar rule as the source itself
  discusses it).

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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
    avoid_months: tuple = (9,),
    trend_window: int = 0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    months = pd.Series(df.index.month, index=df.index)
    calendar_long = ~months.isin(set(avoid_months))

    if trend_window and trend_window > 0:
        sma = close.rolling(trend_window).mean()
        trend_ok = (close > sma).fillna(False)
        position = (calendar_long & trend_ok).astype(int)
    else:
        position = calendar_long.astype(int)

    return position


def generate_returns(
    price_df: pd.DataFrame,
    avoid_months: tuple = (9,),
    trend_window: int = 0,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs here)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        avoid_months=avoid_months,
        trend_window=trend_window,
    )

    daily_returns = close.pct_change().fillna(0.0)
    # Execution-lag convention: trade on yesterday's signal.
    strat_returns = position.shift(1).fillna(0) * daily_returns
    return strat_returns
