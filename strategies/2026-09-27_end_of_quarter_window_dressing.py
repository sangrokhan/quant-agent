"""Strategy: End-of-Quarter Window Dressing calendar seasonality.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-077):
Per QuantifiedStrategies.com's "End of Quarter Effect (Strategy) in the
Stock Market" (https://www.quantifiedstrategies.com/end-of-quarter-effect-strategy/,
read via browser_exec this iteration -- web_search DDGS backend returned
"No results found" on the direct query), the source's own disclosed
mechanical rule is: go long on the 6th-to-last trading day of the calendar
quarter (i.e. long the last quarter_window trading days of the quarter,
default 5), exit at the close of the quarter's final trading day.
Source's own finding: full-sample since 1960 this is a weak, unpromising
edge overall, BUT strongly asymmetric by quarter -- Q4 (driven by the
already-separately-tested Santa Claus Rally window) is by far the best,
Q3/September is poor, and excluding Q4 entirely the strategy's average
per-trade return turns NEGATIVE (-0.11%, 52% win rate). This strategy tests
the source's own unconditional (all-4-quarters) construction as disclosed,
distinct from the already-tested Turn-of-Month (every month, not
quarter-end specifically) and Santa Claus Rally (year-end specific window
only) entries in this repo.

Signal logic
------------
- Identify each calendar quarter's trading days (via price_df's own trading
  calendar, no external holiday calendar needed).
- Entry (long): the quarter_window-th-to-last trading day of the quarter
  (inclusive), i.e. long for the final quarter_window trading days of each
  quarter.
- Exit: close of the quarter's last trading day (flat for the whole next
  quarter until its own final quarter_window days begin).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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
    quarter_window: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    quarter_window: number of trading days at the END of each calendar
        quarter (inclusive of the quarter's final trading day) to hold long.
        Source's own disclosed base case is 5 (entering on the 6th-to-last
        trading day of the quarter).
    """
    df = _prep(price_df)
    close = df["close"]
    idx = close.index

    quarters = pd.PeriodIndex(idx, freq="Q")
    position = pd.Series(0, index=idx, dtype=int)

    for q in quarters.unique():
        mask = quarters == q
        day_positions = idx[mask]
        if len(day_positions) == 0:
            continue
        n = len(day_positions)
        window = min(quarter_window, n)
        last_days = day_positions[n - window:]
        position.loc[last_days] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias -- the trading-day-rank-from-quarter-end
    # is only knowable in hindsight for the CURRENT day at that day's own
    # close, so entering "on" a given day's close means today's OWN close
    # marks entry, and the realized return captured is from that close to
    # tomorrow's close -- standard shift(1) convention matches every other
    # strategy in this repo).
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
