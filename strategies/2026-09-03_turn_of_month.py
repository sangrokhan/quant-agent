"""Strategy: Turn-of-the-Month (TOTM) calendar effect.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-006),
sourced from https://tapescript.io/blog/turn-of-the-month-effect, which
cites Ariel (1987, Journal of Financial Economics) and McConnell & Xu
(2008, Financial Analysts Journal, "Equity Returns at the Turn of the
Month"): from 1926-2005, essentially all of the US stock market's average
positive return occurred in a 4-trading-day window per month -- the last
trading day of the month plus the first three trading days of the next
month -- with the remaining ~15-17 trading days averaging near zero. The
source attributes this to predictable month-end cash flows (paychecks,
401k/retirement contributions, fund rebalancing).

This is a long-only, calendar-based (not price-based) strategy: no moving
averages, no oscillators, no trend/momentum/mean-reversion signal at all --
a completely different signal family from every prior strategy in this
repo's knowledge base (SMA crossover, Bollinger mean-reversion, absolute
momentum with/without trend filter or vol-targeting, RSI(2) mean-reversion).
Tested here on both equity (where the cash-flow mechanism plausibly
applies) and crypto (where it plausibly should NOT, since there's no
payroll/401k cycle driving BTC/ETH demand) as an explicit cross-asset-class
falsification check.

Interface contract for validators (see validation/validators.py) and grid_test.py:
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
    days_before_month_end: int = 1,
    days_after_month_start: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long on the last `days_before_month_end` trading day(s) of a calendar
    month AND the first `days_after_month_start` trading days of the next
    calendar month (the classic Ariel / McConnell-Xu window is
    days_before_month_end=1, days_after_month_start=3, i.e. a 4-trading-day
    window); flat on all other trading days.
    """
    df = _prep(price_df)
    idx = df.index
    ym = pd.Series(idx.year * 100 + idx.month, index=idx)

    # Trading-day rank from the start of each calendar month (0-based) and
    # from the end of each calendar month (0-based, 0 = last trading day).
    rank_from_start = ym.groupby(ym).cumcount()
    rank_from_end = ym.groupby(ym).cumcount(ascending=False)

    near_month_end = rank_from_end < days_before_month_end
    near_month_start = rank_from_start < days_after_month_start

    position = (near_month_end | near_month_start).astype(int)
    position.index = idx
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # Shift position by 1 day: yesterday's signal determines today's exposure
    # (avoid look-ahead bias -- can't trade on today's own close).
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
