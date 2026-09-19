"""Strategy: Conditional "Turnaround Tuesday" -- long Monday close to Tuesday
close, gated by Monday (and optionally Friday) being a down day.

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration's id):
Per TradeQuantiX's "Market Effect Research: Turnaround Tuesday Effect"
(https://www.tradequantixnewsletter.com/p/market-effect-research-turnaround,
read via browser_exec after web_extract's DDG-only backend failed), the
unconditional "always buy Monday close, sell Tuesday close" day-of-week
effect on SPY (1993-2026) is weak and unstable across eras (best day
rotates Monday/Tuesday/Wednesday depending on era). However, the source's
own data shows a much stronger and era-stable conditional effect: when
Monday itself was a DOWN day, the following Tuesday's average return is
"over 2x" the unconditional Tuesday average, and stacking a down Friday on
top of a down Monday amplifies this further (source's own bucket averages:
Friday-up/Monday-up -0.03%, Friday-down/Monday-up -0.03%,
Friday-up/Monday-down +0.10%, Friday-down/Monday-down +0.33% average
Tuesday return). This is behaviorally explained by weekend
news-overreaction on Monday followed by smart-money dip-buying on Tuesday.
First strategy in this repo using a day-of-week-conditional (not
unconditional calendar) entry/exit rule -- prior calendar-effect entries in
this repo (turn-of-month, Santa Claus rally, quad witching) are all
date-of-month/date-of-year triggers, not day-of-week-return-conditional
ones.

Signal logic
------------
- Identify each trading day's weekday (0=Monday .. 4=Friday, per typical
  5-day trading calendar; the data's actual weekday is read directly from
  the DatetimeIndex, robust to holidays shifting the exact date).
- On a Monday: if Monday's own daily return is <= 0 (down day) AND (if
  require_friday_down=True) the prior Friday's return was also <= 0, enter
  long at Monday's close.
- Exit at the very next Tuesday's close (hold exactly one trading day,
  Monday close -> Tuesday close). If no Tuesday immediately follows the
  Monday in the data (e.g. a holiday shifts the calendar), exit at the
  first available following trading day instead, capped at max_hold_days.
- Flat all other days.
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
    require_friday_down: bool = True,
    max_hold_days: int = 2,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change()
    weekday = pd.Series(close.index.weekday, index=close.index)  # 0=Mon

    position = pd.Series(0, index=close.index, dtype=int)
    n = len(close)

    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            # Exit at the next Tuesday (weekday==1) or after max_hold_days,
            # whichever comes first.
            if weekday.iloc[i] == 1 or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            is_monday = weekday.iloc[i] == 0
            monday_down = bool(daily_ret.iloc[i] <= 0) if pd.notna(daily_ret.iloc[i]) else False
            friday_ok = True
            if require_friday_down:
                # Find the most recent Friday before/at this index.
                friday_down = False
                for j in range(i - 1, max(i - 5, -1), -1):
                    if weekday.iloc[j] == 4:
                        friday_ret = daily_ret.iloc[j]
                        friday_down = bool(pd.notna(friday_ret) and friday_ret <= 0)
                        break
                friday_ok = friday_down
            if is_monday and monday_down and friday_ok:
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs).

    Entry is on Monday's own close (same-day trigger, since the signal is
    Monday's own realized return -- this is a same-day-known event, not a
    look-ahead: by market close on Monday, Monday's return is fully
    observed, and we can execute the trade at that same close per the
    source's own "buy Monday close" rule). Exit is Tuesday's close.
    """
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # Position on day i represents "holding into day i's close from day
    # i-1's close" when position.shift(1) is applied elsewhere; here,
    # since entry itself is at Monday's OWN close (not shifted), we need
    # the return realized FROM Monday's close TO Tuesday's close, i.e.
    # tomorrow's return attributed to today's entry signal.
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
