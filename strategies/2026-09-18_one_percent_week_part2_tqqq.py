"""Strategy: "One Percent A Week" Part 2 -- adaptive weekly TQQQ system.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-003):
Per TASC June 2026 Traders' Tips (Dion Kurczek, "One Percent A Week: A
High-Probability Weekly Trading Strategy For TQQQ, Part 2: Variations And
Community Enhancements"), fully disclosed EasyLanguage at
https://traders.com/Documentation/FEEDbk_docs/2026/06/TradersTips.html:
enter long at the first trading day of a new calendar week (Monday-open
approximation, entering at that day's open), then apply five adaptive
exit rules through the week: (1) "momentum failure" -- if day 1 of the
trade showed strength (ProfitPct > FirstDayStrengthPct=2.0%) but day 2
weakens (ProfitPct < NextDayWeakPct=3.0%), exit next bar; (2) hard loss
stop at EntryPrice*HardLossMult=0.985 once ProfitPct drops to
LossArmPct=-1.3% or worse; (3) an EXPANDING profit target
(EntryPrice*TargetMult=1.07, widened by *ExpansionMult=1.011 once
ProfitPct>ExpansionTriggerPct=0.3%) exited via a limit order; (4) a
"recovery" exit on any day after entry where the bar closes below its own
open while still in the trade (weak red bar = give up on this week); (5) a
hard end-of-week (Friday) close-out regardless. Distinct from the two
already-tested "One Percent A Week" variants in this repo (2026-09-12-145
adaptive Part-1 variant with a Tuesday fade-exit only, and 2026-09-13-001
the plain base version with a fixed 1%/0.5% target/stop) -- this Part 2
version adds the momentum-failure day-2 check AND the expanding-target
mechanism AND the close-below-open recovery exit, none of which existed
in the prior two variants tested here.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position series,
    approximated at daily-close granularity since intraday limit/stop fills
    aren't available from this repo's daily-bar loaders -- High/Low used to
    approximate intrabar limit/stop touches where available).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    first_day_strength_pct: float = 2.0,
    next_day_weak_pct: float = 3.0,
    target_mult: float = 1.07,
    expansion_trigger_pct: float = 0.3,
    expansion_mult: float = 1.011,
    recovery_enabled: bool = True,
    loss_arm_pct: float = -1.3,
    hard_loss_mult: float = 0.985,
) -> pd.Series:
    """Return a {0,1} long/flat position series, approximated at daily-close
    granularity per the TASC June 2026 "One Percent A Week Part 2" rules.
    """
    df = _prep(price_df)
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]
    dow = pd.Series(df.index).dt.dayofweek.to_numpy()  # Monday=0

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)

    in_position = False
    entry_price = 0.0
    entry_day_idx = 0
    day_of_trade_week = 0
    first_day_strong = False

    for i in range(n):
        new_week = (i == 0) or (dow[i] < dow[i - 1])
        if new_week:
            day_of_trade_week = 1
        else:
            day_of_trade_week += 1

        if not in_position:
            # enter at the first trading day of a new week, unless today
            # already IS the last trading day before the weekend rollover
            # (mirrors source's "not Friday, next bar is Monday" gate,
            # approximated here as: enter on the first bar of a new week).
            if new_week:
                in_position = True
                entry_price = open_.iloc[i]
                entry_day_idx = i
                first_day_strong = False
                profit_pct = (close.iloc[i] / entry_price - 1.0) * 100.0
                if profit_pct > first_day_strength_pct:
                    first_day_strong = True
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
            continue

        # in position
        held_days = i - entry_day_idx
        profit_pct = (close.iloc[i] / entry_price - 1.0) * 100.0

        exit_now = False

        if held_days == 0:
            # entry day itself: no exit checks (mirrors source's own guard
            # that exit logic only applies once EntryDayOfTradeWeek is set
            # and we've moved past the entry bar).
            position.iloc[i] = 1
            continue

        if held_days == 1 and first_day_strong and profit_pct < next_day_weak_pct:
            exit_now = True
        elif profit_pct <= loss_arm_pct:
            # hard stop: check if low touched the stop level intrabar
            stop_price = entry_price * hard_loss_mult
            if low.iloc[i] <= stop_price:
                exit_now = True
        elif profit_pct > 0:
            target_price = entry_price * target_mult
            if profit_pct > expansion_trigger_pct:
                target_price *= expansion_mult
            if high.iloc[i] >= target_price:
                exit_now = True
        elif recovery_enabled and close.iloc[i] < open_.iloc[i]:
            exit_now = True

        # hard Friday end-of-week exit
        if dow[i] == 4:
            exit_now = True

        if exit_now:
            in_position = False
            position.iloc[i] = 0
        else:
            position.iloc[i] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs).

    Unlike this repo's other strategies (which shift position by 1 day to
    avoid look-ahead since their signals are computed from the CURRENT
    bar's close), this strategy enters at the CURRENT bar's own open and
    exits intrabar on stops/targets/Friday-close, so the position series
    from generate_signals already represents same-day exposure. No
    additional shift is applied here.
    """
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    position = generate_signals(price_df, **kwargs)
    # Approximate same-day entry/exit return as (close/open - 1) while in
    # position on the entry day, and close-to-close return on subsequent
    # held days; exits are captured by position dropping to 0 the same bar
    # the exit condition triggers (so that bar's return uses close/open).
    prev_close = close.shift(1)
    was_in_prev = position.shift(1).fillna(0)
    daily_ret = pd.Series(0.0, index=close.index)
    for i in range(len(close)):
        if position.iloc[i] == 1 and was_in_prev.iloc[i] == 0:
            # entry day: open-to-close return
            daily_ret.iloc[i] = (close.iloc[i] / open_.iloc[i]) - 1.0
        elif position.iloc[i] == 1 and was_in_prev.iloc[i] == 1:
            daily_ret.iloc[i] = (close.iloc[i] / prev_close.iloc[i]) - 1.0
        elif position.iloc[i] == 0 and was_in_prev.iloc[i] == 1:
            # exit day: still held into this bar's session, close-to-close
            daily_ret.iloc[i] = (close.iloc[i] / prev_close.iloc[i]) - 1.0
        else:
            daily_ret.iloc[i] = 0.0
    return daily_ret
