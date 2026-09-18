"""Strategy: MACD zero-line cross confirmed by swing-point (HH/HL) structure.

Hypothesis (see knowledge_base/strategies_log.jsonl for this id):
Per StockCharts.com ChartSchool's "MACD Zero-Line Crosses With Swing Points"
(https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/macd-zero-line-crosses-with-swing-points,
read via browser_exec fallback after web_search's DDGS backend could not
extract page content): a plain MACD zero-line cross is noisy on its own
("subject to producing as much noise as signal"). The source's disclosed
filtering rule: only trust a bullish zero-line cross when price has ALSO
broken above the most recent confirmed swing high (the "H" in the source's
diagrammed H-L range) -- i.e. genuine higher-high (HH) structure is already
underway, not just a lagging MACD threshold cross inside a sideways range.
Symmetrically, exit is driven by price breaking the most recent confirmed
swing LOW (structure failure) rather than waiting for the MACD's own
opposite zero-line cross, which the source explicitly warns "can erase your
profits" if held too long.

Mechanical rule (this repo's own translation of the source's discretionary
chart-reading example into a fully mechanical rule, since the source itself
presents this as a discretionary technique rather than packaged code):
  - Swing high/low: a local pivot high/low over a `swing_window`-bar window
    on each side (a bar is a confirmed swing high if it's the max close of
    the `2*swing_window+1`-bar window centered on it; symmetric for lows).
    Confirmation necessarily lags by `swing_window` bars (only known once
    later bars are in) -- implemented with no look-ahead by only marking a
    swing point "confirmed" swing_window bars after it occurs.
  - Long entry: MACD line crosses above zero AND the close is currently
    above the most recently CONFIRMED swing high (the source's "break above
    the H" condition) -- OR, if MACD is already above zero and a NEW swing
    high gets broken while it stays above zero, that also counts as an
    entry trigger (captures the source's example where price breaks the
    swing high sometime after the initial zero cross, not necessarily on
    the exact same bar).
  - Exit: close breaks below the most recently confirmed swing low
    (structure failure, the source's own preferred trailing-stop-style
    exit) OR MACD crosses back below zero (backstop) OR a max_hold_days
    time-stop.

First strategy in this repo combining a MACD zero-line threshold signal with
a genuine swing-high/swing-low PRICE-STRUCTURE break as both the confirming
entry filter and the primary exit trigger (distinct from 2026-09-03-013's
zero-line-as-signal-line-cross-filter, which uses no price-structure
component at all, and from the Bill Williams Fractals swing-point strategy
2026-09-04-134, which uses fractal breaks with no MACD involvement).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series
    generate_returns(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _macd_line(close: pd.Series, fast: int = 12, slow: int = 26) -> pd.Series:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    return ema_fast - ema_slow


def _confirmed_swings(close: pd.Series, swing_window: int) -> tuple[pd.Series, pd.Series]:
    """Return (confirmed_swing_high, confirmed_swing_low) series, forward-filled,
    with confirmation lagged by swing_window bars (no look-ahead)."""
    n = len(close)
    window = 2 * swing_window + 1
    is_high = pd.Series(False, index=close.index)
    is_low = pd.Series(False, index=close.index)
    values = close.values
    for i in range(swing_window, n - swing_window):
        seg = values[i - swing_window : i + swing_window + 1]
        center = values[i]
        if center == seg.max():
            is_high.iloc[i] = True
        if center == seg.min():
            is_low.iloc[i] = True

    # confirmed swing value, known only swing_window bars later (shift forward)
    swing_high_val = close.where(is_high).shift(swing_window)
    swing_low_val = close.where(is_low).shift(swing_window)
    confirmed_high = swing_high_val.ffill()
    confirmed_low = swing_low_val.ffill()
    return confirmed_high, confirmed_low


def _core(
    price_df: pd.DataFrame,
    macd_fast: int = 12,
    macd_slow: int = 26,
    swing_window: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    macd = _macd_line(close, macd_fast, macd_slow)
    swing_high, swing_low = _confirmed_swings(close, swing_window)

    macd_above_zero = macd > 0
    macd_cross_up = macd_above_zero & ~macd_above_zero.shift(1).fillna(False)
    macd_cross_down = (~macd_above_zero) & macd_above_zero.shift(1).fillna(False)
    break_above_high = (close > swing_high) & (close.shift(1) <= swing_high.shift(1))
    break_below_low = (close < swing_low) & (close.shift(1) >= swing_low.shift(1))

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_days = 0
    for i in range(len(df)):
        if in_pos:
            hold_days += 1
            exit_now = (
                bool(break_below_low.iloc[i])
                or bool(macd_cross_down.iloc[i])
                or hold_days >= max_hold_days
            )
            if exit_now:
                in_pos = False
                hold_days = 0
            else:
                position.iloc[i] = 1
        else:
            entry_now = bool(macd_above_zero.iloc[i]) and (
                bool(macd_cross_up.iloc[i]) or bool(break_above_high.iloc[i])
            )
            if entry_now:
                in_pos = True
                hold_days = 0
                position.iloc[i] = 1
    return position


def generate_signals(
    price_df: pd.DataFrame,
    macd_fast: int = 12,
    macd_slow: int = 26,
    swing_window: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    return _core(price_df, macd_fast, macd_slow, swing_window, max_hold_days)


def generate_returns(
    price_df: pd.DataFrame,
    macd_fast: int = 12,
    macd_slow: int = 26,
    swing_window: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = _core(df, macd_fast, macd_slow, swing_window, max_hold_days)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
