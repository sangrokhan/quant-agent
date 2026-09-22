"""Strategy: Monday weakness reversal (close below prior Friday's low).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-120):
Per QuantifiedStrategies.com's "Is This Still The Best Reversal Strategy?"
(https://www.quantifiedstrategies.com/is-this-still-the-best-reversal-strategy/,
accessed 2026-09-22 via browser_exec after web_extract's ddgs-only backend
could not fetch content), the disclosed rule for their "best reversal
strategy" (tested on SSO, a 2x leveraged SPY ETF) is:

    - Today is Monday.
    - Monday's close is lower than the prior Friday's low (weekend gap-down
      / Monday capitulation).
    - Buy at Monday's close.
    - Exit at the close on the first day the close exceeds yesterday's high
      (rebound confirmation), or after 4 trading days (Friday), whichever
      comes first.

This is distinct from this repo's existing "Turnaround Tuesday" family
(day-of-week unconditional or volume-gated Monday->Tuesday holds,
2026-09-03-018 / 2026-09-04-105 / 2026-09-08-135 / etc.) and from the
"Deep Pullback" mean-reversion entry (2026-09-20-081, uses 15-day-low +
10-day-worst-return conditions, no weekday gate, no explicit Friday-low
reference). Here the trigger is specifically a Monday close breaking below
the *prior Friday's low* (a weekend-gap/quasi-gap-fade construction), with
a rebound-confirmation exit (close > prior day's high) rather than a fixed
day-count or moving-average recross, backstopped by a 4-trading-day
(one calendar week) time-stop matching the source's own disclosed exit
window.

Signal logic
------------
- Compute weekday from the index timestamp (Monday=0).
- entry_signal: weekday==0 (Monday) AND close < (rolling max-of-non-Monday
  lookback proxy for "prior Friday's low"). Since daily bars may skip
  holidays, we approximate "prior Friday" as the most recent prior bar
  whose weekday==4 (Friday); if no Friday bar exists in the last 5 bars
  (e.g. holiday-shortened week), skip the signal that Monday.
- Exit: close > yesterday's high (rebound confirmation) OR
  held >= max_hold_days (default 4 trading days).
- No stop-loss (matches source's disclosed design, which explicitly omits
  one for this strategy).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _find_prior_friday_low(df: pd.DataFrame, lookback: int = 5) -> pd.Series:
    """For each bar, find the low of the most recent bar with weekday==4
    (Friday) within `lookback` bars strictly before the current bar.
    Returns NaN where no such bar exists."""
    idx = df.index
    weekday = pd.Series(idx.weekday, index=idx)
    low = df["low"]

    friday_low = pd.Series(index=idx, dtype=float)
    for i in range(len(idx)):
        found = None
        for back in range(1, lookback + 1):
            j = i - back
            if j < 0:
                break
            if weekday.iloc[j] == 4:
                found = low.iloc[j]
                break
        friday_low.iloc[i] = found if found is not None else float("nan")
    return friday_low


def generate_signals(
    price_df: pd.DataFrame,
    friday_lookback: int = 5,
    max_hold_days: int = 4,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    idx = df.index
    weekday = pd.Series(idx.weekday, index=idx)

    prior_friday_low = _find_prior_friday_low(df, lookback=friday_lookback)

    entry = (weekday == 0) & (close < prior_friday_low)
    entry = entry.fillna(False)

    prior_high = high.shift(1)
    exit_rebound = close > prior_high

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_rebound.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
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
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
