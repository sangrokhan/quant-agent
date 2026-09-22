"""Strategy: Turn-of-the-Month (Ultimo Effect) calendar seasonality.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-065):
Per QuantifiedStrategies.com's "The Turn Of The Month Trading Strategy
(Ultimo Effect) - Backtest and Trading Rules"
(https://www.quantifiedstrategies.com/turn-of-the-month-trading-strategy/,
read via browser_exec this iteration -- web_search's DDGS backend
intermittently TLS-erroring), the "turn of the month" (Ultimo) effect is a
well-documented calendar anomaly: stock returns are abnormally strong
around month-end and the first few trading days of the new month, likely
driven by structural institutional flows (payroll investing, fund
rebalancing). Source's disclosed rule: "go long at the close on the fifth
last trading day of the month, and exit after seven days, i.e. at the
close of the third trading day of the next month" (~33% market exposure
time). Source reports S&P 500 since 1960: CAGR 7.11% (vs buy-hold 6.95%)
with MDD 27% (vs buy-hold 56%) when invested ONLY during this window.
First calendar/seasonality "turn of month" strategy in this repo (0 prior
KB hits for "Turn of month effect").

Signal logic
------------
- Purely calendar-driven, no price-derived indicator. For each bar, compute
  its trading-day-of-month rank both counting forward (1st, 2nd, 3rd...)
  and counting backward from month-end (1st-to-last, 2nd-to-last...) using
  ONLY the trading days actually present in the price_df's index (handles
  weekends/holidays automatically since price_df only contains trading
  days).
- Long entry: today is exactly the Nth-to-last trading day of its calendar
  month (default N=5, source's disclosed rule).
- Exit: exactly hold_days trading days after entry (default 7, source's
  disclosed rule -- this lands close to the 3rd trading day of the next
  month for N=5).
- Flat otherwise. Long-only (no short per SAFETY.md scope). No trend
  filter or other indicator -- this is a pure calendar effect per the
  source's own framing (though the underlying asset's trend can obviously
  still affect performance across an evaluation window with only a handful
  of net-long months).

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py):
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
    entry_days_before_month_end: int = 5,
    hold_days: int = 7,
) -> pd.Series:
    df = _prep(price_df)
    idx = df.index

    # Group trading days by (year, month); rank each day's position from
    # month-end (1 = last trading day of month, 2 = 2nd-to-last, etc.)
    ym = pd.Series(idx.tz_localize(None) if idx.tz is not None else idx).dt.to_period("M").values
    days_before_end_vals = [0] * len(idx)
    start = 0
    for m in range(len(idx)):
        if m == len(idx) - 1 or ym[m + 1] != ym[m]:
            n = m - start + 1
            for j, pos in enumerate(range(start, m + 1)):
                days_before_end_vals[pos] = n - j
            start = m + 1
    days_before_end = pd.Series(days_before_end_vals, index=idx)

    entry_trigger = (days_before_end == entry_days_before_month_end)

    position = pd.Series(0, index=idx, dtype=int)
    in_position = False
    entry_idx = -1
    for i in range(len(idx)):
        if not in_position:
            if bool(entry_trigger.iloc[i]):
                in_position = True
                entry_idx = i
        else:
            held = i - entry_idx
            if held >= hold_days:
                in_position = False
                # allow immediate re-entry same bar if trigger also true
                if bool(entry_trigger.iloc[i]):
                    in_position = True
                    entry_idx = i
        position.iloc[i] = 1 if in_position else 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    entry_days_before_month_end: int = 5,
    hold_days: int = 7,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        df,
        entry_days_before_month_end=entry_days_before_month_end,
        hold_days=hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
