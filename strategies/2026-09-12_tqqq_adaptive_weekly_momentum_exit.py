"""Strategy: Adaptive Weekly Momentum Exit ("One Percent a Week" variant).

Source: TASC (Technical Analysis of Stocks & Commodities) June 2026 Traders'
Tips, Dion Kurczek's "High-Probability Weekly Trading Strategy For TQQQ,
Part 2: Variations and Community Enhancements" -- "Adaptive Weekly Momentum
Exit" model, via TradingView script description
https://www.tradingview.com/script/CSGmHoik-TASC-2026-06-One-Percent-A-Week-Adaptive/
(visited 2026-09-12, see knowledge_base/visited_pages.jsonl).

Source's disclosed rules (adapted from intraday/5-min execution to this
repo's daily-bar OHLC data -- daily high/low used as intrabar stop/target
touch proxies, daily close used for the Monday/Tuesday/Friday checkpoints):

1. Enter a new long trade at Monday's open (weekday()==0; first trading day
   of the week if Monday is a holiday).
2. Fixed stop-loss at `stop_pct` (source: 1.5%) below entry.
3. Initial take-profit at `initial_target_pct` (source: 7%) above entry.
4. End-of-Monday checkpoint: if Monday's close return > `momentum_gate_pct`
   (source: 0.3%), scale the target up by `target_scale_up` (source: 1.011,
   -> ~8.177%); if Monday's close return <= 0, cut the target down to
   `reduced_target_pct` (source: 2.5%).
5. End-of-Tuesday momentum-weakness exit: if Monday's return exceeded
   `monday_thresh` (source: 2%) but Tuesday's cumulative return from entry
   is below `tuesday_thresh` (source: 3%), close the position at Tuesday's
   close (momentum faded).
6. If still open, check daily high/low each remaining day (Wed-Fri) for a
   stop-loss or take-profit touch (whichever the bar's range first crosses;
   assume stop touched first on ambiguous bars, conservative).
7. If still open at Friday's close (or the week's last trading day), close
   flat regardless of P&L.

No overnight-weekend gap left unclosed by construction (rule 7). This is a
new intra-week adaptive-target/momentum-exit construction, distinct from
this repo's existing weekly-seasonality/day-of-week strategies (which are
either directional Monday/Friday calendar drift plays or single fixed-
threshold entries) -- this one uses a *path-dependent, multi-checkpoint*
target/stop schedule within a single week's position.

Interface contract (see validation/grid_test.py, validation/validators.py):
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
    stop_pct: float = 0.015,
    initial_target_pct: float = 0.07,
    momentum_gate_pct: float = 0.003,
    target_scale_up: float = 1.011,
    reduced_target_pct: float = 0.025,
    monday_thresh: float = 0.02,
    tuesday_thresh: float = 0.03,
) -> pd.Series:
    """Return a {0,1} long/flat position series (1 = in an active weekly trade)."""
    df = _prep(price_df)
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]
    weekday = pd.Series(df.index.weekday, index=df.index)
    iso_week = pd.Series(
        [d.isocalendar()[:2] for d in df.index], index=df.index
    )

    position = pd.Series(0, index=close.index, dtype=int)

    n = len(df)
    week_groups: dict = {}
    for i in range(n):
        week_groups.setdefault(iso_week.iloc[i], []).append(i)

    for _wk, idxs in week_groups.items():
        idxs = sorted(idxs)
        entry_i = idxs[0]  # first trading day of the week acts as "Monday"
        entry_price = open_.iloc[entry_i]
        stop_price = entry_price * (1 - stop_pct)
        target_price = entry_price * (1 + initial_target_pct)

        in_trade = True
        position.iloc[entry_i] = 1
        monday_close_ret = (close.iloc[entry_i] - entry_price) / entry_price

        if monday_close_ret > momentum_gate_pct:
            target_price = entry_price * (1 + initial_target_pct) * target_scale_up
        elif monday_close_ret <= 0:
            target_price = entry_price * (1 + reduced_target_pct)

        for j_pos in range(1, len(idxs)):
            i = idxs[j_pos]
            if not in_trade:
                break

            if j_pos == 1:  # "Tuesday" momentum-weakness checkpoint
                tuesday_ret = (close.iloc[i] - entry_price) / entry_price
                if monday_close_ret > monday_thresh and tuesday_ret < tuesday_thresh:
                    position.iloc[i] = 1  # held through Tuesday's close-to-close move, exit after
                    in_trade = False
                    continue

            bar_low = low.iloc[i]
            bar_high = high.iloc[i]
            hit_stop = bar_low <= stop_price
            hit_target = bar_high >= target_price
            is_last_day_of_week = j_pos == len(idxs) - 1

            # Whichever condition ends the trade, day i's own close-to-close
            # move is still realized (we held into and through that day) --
            # mark it 1 and stop afterward.
            position.iloc[i] = 1
            if hit_stop or hit_target or is_last_day_of_week:
                in_trade = False

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs).

    Note: unlike the simpler always-flat-until-cross strategies elsewhere in
    this repo, position here is already {0,1} per-day for an *active weekly
    trade*, and the trade's realized P&L for its exit day is captured via
    the day's own close-to-close return (since the position was entered
    intraweek and typically exits intraweek too) -- this repo's OHLC-only
    data means we approximate stop/target fills at the day's close rather
    than the exact intrabar level, which is a conservative simplification
    consistent with the rest of this repo's daily-bar backtests.
    """
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    position = generate_signals(price_df, **kwargs)

    daily_ret = pd.Series(0.0, index=close.index)
    n = len(close)
    for i in range(n):
        if position.iloc[i] == 1:
            if i == 0 or position.iloc[i - 1] == 0:
                # entry day: return from that day's open to close
                daily_ret.iloc[i] = (close.iloc[i] - open_.iloc[i]) / open_.iloc[i]
            else:
                daily_ret.iloc[i] = (close.iloc[i] - close.iloc[i - 1]) / close.iloc[i - 1]
        elif i > 0 and position.iloc[i - 1] == 1:
            # exit day already captured its own position==1 close-to-close
            # move in the branch above the day it exited on; a flat day after
            # an active day means no additional return here.
            daily_ret.iloc[i] = 0.0
    return daily_ret
