"""Strategy: Turn-of-the-Month (Ultimo Effect) calendar seasonality, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per quantifiedstrategies.com's "The Turn Of The Month Trading Strategy
(Ultimo Effect)" article (visited this iteration via browser_exec,
web_search DDGS backend TLS-connection-errored on the query): stock market
returns are disproportionately concentrated around month boundaries,
likely driven by structural institutional flows (month-end
rebalancing/payroll-driven inflows). Disclosed rule: go long at the close
of the 5th-to-last trading day of the month, exit at the close of the 3rd
trading day of the following month (holding through month-end and into
the new month) -- roughly 1/3 of trading days invested. Source's own
S&P-500-since-1960 backtest: CAGR 7.11% vs. buy-and-hold 6.95%, with max
drawdown 27% vs. buy-and-hold's 56% -- a materially better risk-adjusted
profile despite similar raw CAGR, from ~1/3 market exposure. Source
explicitly claims "the effect persists across stocks, bonds, and crypto."

First pure calendar/turn-of-month strategy in this repo distinct from
already-tested single-day-of-week/single-day-of-month calendar anomalies
(e.g. "Sell in August", "Turnaround Tuesday", day-of-month seasonality
already logged elsewhere) -- this is a multi-day WINDOW spanning two
different calendar months (last N trading days of month M through first M
trading days of month M+1), not a single fixed calendar date/weekday.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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
    last_n_days: int = 5,
    first_n_days: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: the `last_n_days`-th-to-last trading day of the month
    (i.e. entering the position at the close of that day, per the source's
    disclosed rule).
    Long while: still within the last `last_n_days` trading days of the
    month, OR within the first `first_n_days` trading days of the new
    month.
    Exit to flat: at the close of the `first_n_days`-th trading day of the
    new month.
    """
    df = _prep(price_df)
    close = df["close"]
    idx = close.index

    # Trading-day-of-month counters (1-indexed), computed per calendar month.
    month_key = idx.to_series().dt.to_period("M")
    day_of_month_asc = month_key.groupby(month_key).cumcount() + 1
    day_of_month_desc = month_key.groupby(month_key).cumcount(ascending=False) + 1

    in_last_n = day_of_month_desc.values <= last_n_days
    in_first_n = day_of_month_asc.values <= first_n_days

    position_flags = in_last_n | in_first_n
    position = pd.Series(position_flags.astype(int), index=close.index)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
