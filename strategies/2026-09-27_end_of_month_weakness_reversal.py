"""Strategy: End-of-Month calendar-day weakness reversal (SPY/QQQ).

Hypothesis (see knowledge_base/strategies_log.jsonl entry for this
iteration's id): Per QuantifiedStrategies.com's "End of Month Trading
Strategy 2026- S&P500 Outperformance!"
(https://www.quantifiedstrategies.com/end-of-month-trading-strategy/,
read via browser_exec this iteration -- web_search returned only snippet
results, browser_exec used to read the full page directly), the
end-of-month seasonality effect is exploited by requiring a NEGATIVE
close on a specific late-CALENDAR-day (day 29, 30, or 31 of the month --
not trading day count) before entering long at the close; the source's
own disclosed exit is either two successive positive closes in a row, or
a fixed profit target (source's own worked example uses 1% on SPY), with
no stop-loss.

This repo has many turn-of-month/end-of-month calendar entries (e.g.
2026-09-03-006, 2026-09-06-169, 2026-09-11-124/125, 2026-09-22-065/066,
2026-09-23-001), but none require this specific "wait for a NEGATIVE
close on a specific late-calendar-day" trigger combined with a
"two-successive-positive-closes OR profit-target" exit -- most prior
entries use a fixed calendar WINDOW (buy N days before month end
regardless of that day's direction) rather than this source's explicit
conditional weakness trigger + adaptive early-exit rule.

Signal logic
------------
- calendar_day = the day-of-month (1-31) of each bar's timestamp.
- Entry trigger day: calendar_day is in {29, 30, 31} (source's exact
  disclosed rule; note this excludes months where day 29-31 falls on a
  weekend/holiday and has no trading bar that calendar day -- handled
  naturally since we only look at bars that exist).
- Entry: if the trigger day's own close is negative (close < prior close)
  -> enter long at that bar's close.
- Exit: at the close, once TWO CONSECUTIVE closes since entry are each
  higher than the prior close (source's "two successive positive closes
  in a row"), OR cumulative return since entry hits >= profit_target
  (source's own worked example: 1%), whichever comes first. No stop-loss
  in the source; max_hold_days safety valve added (this repo's
  convention) since the source's own exit conditions could in principle
  never fire.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position).
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
    profit_target: float = 0.01,
    max_hold_days: int = 15,
    trigger_days: tuple = (29, 30, 31),
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    prev_close = close.shift(1)
    daily_up = close > prev_close

    calendar_day = df.index.day
    is_trigger_day = pd.Series(calendar_day, index=close.index).isin(trigger_days)
    trigger_negative = is_trigger_day & (~daily_up)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_price = None
    consecutive_up = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            cum_ret = (close.iloc[i] / entry_price) - 1.0 if entry_price else 0.0
            if bool(daily_up.iloc[i]):
                consecutive_up += 1
            else:
                consecutive_up = 0
            exit_now = (consecutive_up >= 2) or (cum_ret >= profit_target) or (held >= max_hold_days)
            if exit_now:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(trigger_negative.iloc[i]) if pd.notna(trigger_negative.iloc[i]) else False:
                in_position = True
                entry_idx = i
                entry_price = close.iloc[i]
                consecutive_up = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strategy_ret
