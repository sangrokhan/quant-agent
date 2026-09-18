"""Strategy: "Sell in August and Go Away" -- 10-month calendar seasonality
(buy end-October, sell end-July, flat August-October).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-003):
Per Cesar Alvarez (Alvarez Quant Trading),
https://alvarezquanttrading.com/blog/sell-in-august-and-go-away/ (read via
browser_exec fallback after web_search DDGS/Yahoo backend TLS-errored on
every query this iteration), re-testing Jay Kaeppel's TASC Nov 2019
"Stock Market Seasonality: A Global Phenomenon" (buy end-October, sell
end-April, the classic "sell in May" 6-month hold) across 18 country ETFs
plus SPY. Alvarez's own finding: this classic 6-month hold was the best
choice in 13/18 ETFs for 1997-2011, but the regime clearly shifted
post-2012 -- for 2012-2023, buying end-October and holding through
end-JULY (a 10-month hold, NOT the classic 6-month Oct-Apr) was the best
choice in 12/18 ETFs (vs the classic split winning only 4/18), which
Alvarez attributes to the Fed keeping post-2012 bear markets shorter/
milder. This is the source's own exact disclosed rule ("buy on the last
day of month X at the close, hold for Y months, sell at close on the
last day of the month", with X=10 (October), Y=9 (nine months later =
end of July)).

Distinct from this repo's already-tested classic Sell-in-May/Halloween
Effect (2026-09-09-019, 2026-09-09-020, 2026-09-16-187 -- all use the
6-month Nov-Apr split) via the 10-month Oct-Jul hold window that
Alvarez's own post-2012 backtest found superior.

Interface contract for validators (see validation/validators.py) and
grid_test.py: both generate_signals and generate_returns accept all
tunable parameters as keyword arguments.
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
    entry_month: int = 10,   # buy at close of last trading day of this month
    hold_months: int = 9,    # hold for this many months (10=Oct + 9 = end of July)
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long from the close of the last trading day of `entry_month` each
    year, held for `hold_months` calendar months (i.e. exit at the close
    of the last trading day of the (entry_month + hold_months)-th month),
    flat otherwise. Standard calendar-seasonality construction identical
    in spirit to this repo's other end-of-month-anchored strategies
    (e.g. turn-of-month, holiday-calendar effects).
    """
    df = _prep(price_df)
    close = df["close"]
    idx = close.index

    # Identify "last trading day of each month" markers.
    month_period = idx.to_period("M")
    is_last_day_of_month = month_period != month_period.shift(-1, freq=None) if False else None
    # Simpler: a day is the last trading day of its month if the NEXT
    # trading day (if any) falls in a different month.
    next_month_period = pd.Series(month_period).shift(-1)
    is_month_end = (pd.Series(month_period, index=idx) != next_month_period.values)
    is_month_end.iloc[-1] = True  # last bar in the whole series counts too

    months = pd.Series(idx.month, index=idx)

    position = pd.Series(0, index=idx, dtype=int)
    in_position = False
    exit_target_period = None

    month_periods_arr = month_period
    for i in range(len(idx)):
        cur_period = month_periods_arr[i]
        if in_position:
            if is_month_end.iloc[i] and cur_period == exit_target_period:
                position.iloc[i] = 1  # still in through exit day close signal handled by shift in returns
                in_position = False
            else:
                position.iloc[i] = 1
        else:
            if is_month_end.iloc[i] and months.iloc[i] == entry_month:
                in_position = True
                position.iloc[i] = 1
                exit_target_period = cur_period + hold_months
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
