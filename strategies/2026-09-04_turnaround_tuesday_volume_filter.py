"""Strategy: Turnaround Tuesday (Monday close -> Tuesday close) gated by a
volume filter (only enter if Monday's volume exceeds its own trailing
average) -- a targeted revisit of the previously-rejected strategy
2026-09-04-018 / 2026-09-03-018.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-105):
The plain Turnaround Tuesday day-of-week strategy (long Monday close ->
Tuesday close) was already tested in this repo (2026-09-03-018) and
rejected: full-sample Sharpe 0.81 on QQQ (below the 1.0 threshold) and an
unstable "best weekday" across the sample (Monday actually beat Tuesday on
SPY). Per QuantifiedStrategies.com's own A/B-tested finding (Volume
Trading Strategy article), gating the SAME Turnaround Tuesday entry by
whether the trigger day's volume exceeds its own 25-day moving average
meaningfully improved results in their own SPY backtest: avg gain/trade
0.81% (high-volume Mondays) vs 0.41% (low-volume Mondays), AND a LOWER max
drawdown (23% vs 27%) for the high-volume variant. This is a targeted fix
addressing the -018 rejection reason directly (the raw day-of-week signal
alone is too weak/unstable; the source's own evidence says adding a volume
filter should help), not a from-scratch new hypothesis.

Signal logic
------------
- Trigger day = `entry_weekday` (default 0 = Monday, ISO weekday()==0).
- Volume filter: trigger day's volume must exceed `vol_window`-day
  trailing average volume (computed using the PRIOR `vol_window` days,
  not including the trigger day itself, to avoid look-ahead) times
  `vol_multiplier` (default 1.0, i.e. simply "above average").
- Entry (long): on the trigger day's close, if the volume filter passes.
- Exit: on the close of the day `hold_days` trading days later (default 1,
  i.e. Monday close -> Tuesday close, same horizon as the original -018
  strategy for a clean apples-to-apples comparison).
- Long-only, flat otherwise.

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
    entry_weekday: int = 0,
    hold_days: int = 1,
    vol_window: int = 25,
    vol_multiplier: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    volume = df["volume"]
    trailing_avg_vol = volume.shift(1).rolling(vol_window).mean()

    weekdays = df.index.weekday
    is_trigger_day = weekdays == entry_weekday
    vol_ok = volume > (trailing_avg_vol * vol_multiplier)
    entry_trigger = is_trigger_day & vol_ok.fillna(False)

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    hold_remaining = 0
    for i in range(n):
        if hold_remaining > 0:
            position.iloc[i] = 1
            hold_remaining -= 1
        elif bool(entry_trigger.iloc[i]):
            position.iloc[i] = 1
            hold_remaining = hold_days
        else:
            position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    entry_weekday: int = 0,
    hold_days: int = 1,
    vol_window: int = 25,
    vol_multiplier: float = 1.0,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df, entry_weekday=entry_weekday, hold_days=hold_days,
        vol_window=vol_window, vol_multiplier=vol_multiplier,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
