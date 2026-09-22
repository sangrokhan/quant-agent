"""Strategy: Sell-in-May + SMA trend filter (rescue of 2026-09-22-067).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-068):
Direct rescue attempt for this same cron trigger's prior rejection
2026-09-22-067 (Sell-in-May/Halloween Effect, decisive fail on both QQQ
Sharpe 0.675/MDD 0.286 and SPY Sharpe 0.580/MDD 0.341 -- both MDD failures
driven by holding through the full Nov-Apr window with no risk
management). That report's own suggested next step: "add a trend/
volatility filter within the Nov-Apr window (skip or reduce exposure
during a confirmed downtrend), similar to the turn-of-month rescue
(2026-09-22-066)". This iteration adds exactly that: same Nov-Apr calendar
window from 2026-09-22-067, but exposure is additionally gated on
close > SMA(trend_window) -- flat even during the "buy" calendar window if
the underlying is in a confirmed downtrend, checked daily (not just at
window entry).

Signal logic
------------
- Same calendar window as 2026-09-22-067: long-eligible when month is in
  [long_start_month..long_end_month] (wrapping Nov-Apr by default).
- Additional daily gate: only actually long when ALSO close > SMA(trend_window)
  (continuously re-evaluated each bar within the window, so exposure can
  flip off mid-window on a trend break and back on if price recovers above
  the SMA before the window ends).
- Flat outside the calendar window, or when in the window but in a
  downtrend. Long-only (no short per SAFETY.md scope).

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
    long_start_month: int = 11,
    long_end_month: int = 4,
    trend_window: int = 100,
) -> pd.Series:
    df = _prep(price_df)
    idx = df.index
    months = idx.tz_localize(None).month if idx.tz is not None else idx.month

    if long_start_month > long_end_month:
        in_calendar_window = (months >= long_start_month) | (months <= long_end_month)
    else:
        in_calendar_window = (months >= long_start_month) & (months <= long_end_month)

    close = df["close"]
    sma_trend = close.rolling(trend_window).mean()
    uptrend = (close > sma_trend).fillna(False)

    position = pd.Series((pd.Series(in_calendar_window, index=idx) & uptrend).astype(int), index=idx)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    long_start_month: int = 11,
    long_end_month: int = 4,
    trend_window: int = 100,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        df,
        long_start_month=long_start_month,
        long_end_month=long_end_month,
        trend_window=trend_window,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
