"""Strategy: Fibonacci Time Zone reversal with candlestick confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-094):
Per https://fxnx.com (via Google AI-overview synthesis of FXNX/Fusion
Markets/TradingView Fibonacci Time Zone guides): vertical time lines
projected at Fibonacci-sequence day-counts (1,2,3,5,8,13,21,34,55,89,...)
forward from a major swing low mark statistically favored "turning
windows" where a reversal is more likely to occur than on a random day.
The source's exact rule set: anchor at a major swing extreme, wait for
price to approach a projected time-zone line within a 1-2 bar window,
require a bullish/bearish reversal candle confirming right at the zone,
enter on that confirmation, stop past the immediate swing extreme (here
approximated with an ATR multiple), and use a time-based invalidation
exit if the reversal fails to develop within a couple of bars, or a
profit target at the next sequential time-zone line (approximated here
with a max_hold_days time-stop, since a literal "next line" target is
awkward to backtest generically across assets).

This is the first Fibonacci Time Zone (day-count projection) strategy in
this repo -- distinct from Fibonacci retracement/extension (price-ratio
based, not time-based) and from generic swing-pivot strategies (Zig Zag,
Andrews Pitchfork), because the entry condition here is gated on being
within `tolerance_days` of a projected Fibonacci *day count* from the
most recent swing low, not on any price level.

Signal logic
------------
- A swing low is confirmed at bar i when close[i] is the lowest close in
  the trailing `swing_window` bars (no look-ahead: only uses data up to
  and including bar i). Each new swing low re-anchors the projection.
- From the most recent anchor bar, project forward the Fibonacci sequence
  of day offsets (1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, ...) up to
  `max_offset`. A bar is "in an active time zone" if the number of bars
  since the anchor is within `tolerance_days` of any of these offsets.
- Entry (long): bar is in an active time zone AND a bullish reversal
  candle confirms (close > open AND close > previous close, i.e. an
  up-close reversal bar) AND we are not already in a position.
- Exit: close falls below (entry_price - atr_mult * ATR(14)) [stop-loss
  approximating "beyond the immediate swing extreme"], OR a
  max_hold_days time-stop (approximating "exit if reversal fails to
  develop" / "target next time-zone line").

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


def _fib_sequence(max_offset: int) -> list:
    seq = [1, 2, 3]
    while seq[-1] < max_offset:
        seq.append(seq[-1] + seq[-2])
    return [x for x in seq if x <= max_offset]


def _atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 20,
    max_offset: int = 144,
    tolerance_days: int = 1,
    atr_window: int = 14,
    atr_mult: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    n = len(close)

    # Confirm swing lows (no look-ahead): close[i] is the trailing-window min.
    rolling_min = close.rolling(swing_window).min()
    is_swing_low = (close == rolling_min).fillna(False)

    fib_offsets = _fib_sequence(max_offset)
    atr = _atr(df, atr_window)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_price = None
    anchor_idx = None

    for i in range(n):
        if bool(is_swing_low.iloc[i]):
            anchor_idx = i

        in_active_zone = False
        if anchor_idx is not None:
            days_since = i - anchor_idx
            for off in fib_offsets:
                if abs(days_since - off) <= tolerance_days:
                    in_active_zone = True
                    break

        if in_position:
            held = i - entry_idx
            atr_val = atr.iloc[i]
            stop_hit = False
            if entry_price is not None and atr_val == atr_val and atr_val is not None:
                stop_hit = close.iloc[i] < (entry_price - atr_mult * atr_val)
            if stop_hit or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                entry_price = None
                continue
            position.iloc[i] = 1
        else:
            bullish_reversal = False
            if i > 0:
                bullish_reversal = bool(
                    close.iloc[i] > open_.iloc[i] and close.iloc[i] > close.iloc[i - 1]
                )
            if in_active_zone and bullish_reversal:
                in_position = True
                entry_idx = i
                entry_price = close.iloc[i]
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
