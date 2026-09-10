"""Strategy: Sy Harding's Seasonal Timing Strategy (Best Six Months + MACD trigger).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per QuantifiedStrategies.com's "Sy Harding's Seasonal Timing Strategy"
(https://www.quantifiedstrategies.com/sy-hardings-seasonal-timing-strategy/,
visited this iteration via browser_exec fallback), Sy Harding enhanced the
Stock Trader's Almanac's "Best Six Months" (long Nov-Apr, flat May-Oct)
calendar effect by using MACD crossovers to fine-tune the exact entry/exit
day around the anchor dates, rather than a fixed calendar switch. Source's
own disclosed exact rule:
  - Daily bars, standard MACD (fast=12, slow=26, signal=9).
  - Buy rule: on October 16 (or the next trading day it can act on),
    if the MACD line is above its signal line AND currently flat, buy at
    that day's close.
  - Sell rule: on April 21 (or the next trading day), if the MACD line is
    below its signal line AND currently long, sell at that day's close.
  - If the MACD condition is NOT met on the anchor date, the source's
    original design holds the existing position (stays long past April 21,
    or stays out past October 16) until the MACD condition is later met OR
    a max lookforward window elapses (this repo operationalizes the latter
    as `anchor_lookforward_days`, since the source itself doesn't specify
    an unbounded wait).

This is the first Sy Harding "Best Six Months + MACD" combined
seasonal-anomaly-plus-technical-trigger strategy in this repo -- distinct
from all prior pure-calendar Sell-in-May/Halloween variants (2026-09-09-019/
020, both rejected on Sharpe/MDD with NO technical trigger refinement) and
distinct from every other MACD strategy (crossover/zero-line/histogram),
since here MACD is used only as a narrow-window ENTRY/EXIT TIMING TRIGGER
anchored to two specific calendar dates, not a standalone signal.

Interface contract for validators (see validation/validators.py) /
grid_test.py (see validation/grid_test.py):
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


def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


def generate_signals(
    price_df: pd.DataFrame,
    entry_month: int = 10,
    entry_day: int = 16,
    exit_month: int = 4,
    exit_day: int = 21,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    anchor_lookforward_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Around each year's entry anchor date (entry_month/entry_day): scan
    forward up to anchor_lookforward_days trading days for the first day
    the MACD line is above its signal line; buy that day (if not already
    long). Around each year's exit anchor date (exit_month/exit_day):
    scan forward up to anchor_lookforward_days trading days for the first
    day the MACD line is below its signal line; sell that day (if long).
    Position is held flat/long between trigger events.
    """
    df = _prep(price_df)
    close = df["close"]
    macd_line, signal_line = _macd(close, macd_fast, macd_slow, macd_signal)
    bullish_macd = (macd_line > signal_line).fillna(False)
    bearish_macd = (macd_line < signal_line).fillna(False)

    index = df.index
    n = len(index)
    dates = pd.Series(index).dt.date
    months = pd.Series(index).dt.month.to_numpy()
    days = pd.Series(index).dt.day.to_numpy()

    # Find anchor-date bar indices (first bar on/after the anchor date each year).
    years = sorted(set(pd.Series(index).dt.year))
    entry_anchor_idx = {}
    exit_anchor_idx = {}
    for y in years:
        # entry anchor
        target = pd.Timestamp(year=y, month=entry_month, day=entry_day, tz=index.tz)
        pos = index.searchsorted(target)
        if pos < n:
            entry_anchor_idx[y] = pos
        # exit anchor
        target2 = pd.Timestamp(year=y, month=exit_month, day=exit_day, tz=index.tz)
        pos2 = index.searchsorted(target2)
        if pos2 < n:
            exit_anchor_idx[y] = pos2

    position = [0] * n
    in_pos = False
    bullish_arr = bullish_macd.to_numpy()
    bearish_arr = bearish_macd.to_numpy()

    # Build a sorted list of (bar_idx, event_type) anchor events.
    events = []
    for y, idx0 in entry_anchor_idx.items():
        events.append((idx0, "entry"))
    for y, idx0 in exit_anchor_idx.items():
        events.append((idx0, "exit"))
    events.sort(key=lambda e: e[0])

    for start_idx, ev_type in events:
        end_idx = min(start_idx + anchor_lookforward_days, n)
        if ev_type == "entry" and not in_pos:
            for i in range(start_idx, end_idx):
                if bullish_arr[i]:
                    in_pos = True
                    break
        elif ev_type == "exit" and in_pos:
            for i in range(start_idx, end_idx):
                if bearish_arr[i]:
                    in_pos = False
                    break
        # Fill position forward from start_idx to the next event (or end)
        # is handled by the final pass below using in_pos snapshots per bar.

    # Second pass: replay events in order, marking position array segment by
    # segment (simpler and avoids overlapping-fill bugs from the loop above).
    in_pos = False
    position = [0] * n
    cursor = 0
    for start_idx, ev_type in events:
        # Fill unchanged position up to start_idx.
        for i in range(cursor, min(start_idx, n)):
            position[i] = 1 if in_pos else 0
        end_idx = min(start_idx + anchor_lookforward_days, n)
        triggered_at = None
        if ev_type == "entry" and not in_pos:
            for i in range(start_idx, end_idx):
                if bullish_arr[i]:
                    triggered_at = i
                    break
        elif ev_type == "exit" and in_pos:
            for i in range(start_idx, end_idx):
                if bearish_arr[i]:
                    triggered_at = i
                    break

        if triggered_at is not None:
            for i in range(start_idx, triggered_at):
                position[i] = 1 if in_pos else 0
            in_pos = not in_pos
            for i in range(triggered_at, end_idx):
                position[i] = 1 if in_pos else 0
            cursor = end_idx
        else:
            for i in range(start_idx, min(start_idx + 1, n)):
                position[i] = 1 if in_pos else 0
            cursor = start_idx + 1

    for i in range(cursor, n):
        position[i] = 1 if in_pos else 0

    return pd.Series(position, index=df.index, dtype=int).rename("position")


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret.rename("returns")
