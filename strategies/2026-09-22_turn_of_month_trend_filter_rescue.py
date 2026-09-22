"""Strategy: Turn-of-the-Month + SMA trend filter (rescue of near-miss 2026-09-22-065).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-066):
Direct rescue attempt for this same cron trigger's prior near-miss
2026-09-22-065 (Turn-of-Month Ultimo Effect, QQQ Sharpe 0.895/SPY Sharpe
0.883, both <1.0 threshold, but all other 4/5 validators passed cleanly on
both symbols including a perfect 4/4 walk-forward and very robust
parameter sensitivity). That report's own suggested next step: "combine
the calendar entry with a simple trend filter (e.g. skip entries when the
broader market is in a confirmed downtrend)". This iteration adds exactly
that: the same Nth-to-last-trading-day entry + fixed hold_days exit from
2026-09-22-065, but the entry is additionally gated on close > SMA(200)
(this repo's standard uptrend filter, used in >50 other strategies here)
at the moment of entry, skipping the turn-of-month trade entirely in
confirmed-downtrend months.

Signal logic
------------
- Same calendar entry timing as 2026-09-22-065: entry_days_before_month_end
  Nth-to-last trading day of the month.
- Additional gate: only enter if close > SMA(trend_window) on the entry
  bar (skip the trade in a downtrend month).
- Exit: fixed hold_days trading days after entry (unconditional, same as
  base strategy -- no early trend-based exit, since the position is
  already short-duration/low-exposure by design).
- Flat otherwise. Long-only (no short per SAFETY.md scope).

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
    trend_window: int = 200,
) -> pd.Series:
    df = _prep(price_df)
    idx = df.index
    close = df["close"]
    sma_trend = close.rolling(trend_window).mean()
    uptrend = (close > sma_trend).fillna(False)

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

    calendar_trigger = (days_before_end == entry_days_before_month_end)
    entry_trigger = (calendar_trigger & uptrend).fillna(False)

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
                if bool(entry_trigger.iloc[i]):
                    in_position = True
                    entry_idx = i
        position.iloc[i] = 1 if in_position else 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    entry_days_before_month_end: int = 5,
    hold_days: int = 7,
    trend_window: int = 200,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        df,
        entry_days_before_month_end=entry_days_before_month_end,
        hold_days=hold_days,
        trend_window=trend_window,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
