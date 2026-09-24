"""Strategy: Bulkowski Tall Candle Setup -- trading minor lows (long only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-134):
Per https://thepatternsite.com/TallCandleSetup.html (Thomas Bulkowski,
browser_exec), a "tall candle" (today's high-low range > 146% of the
22-day trailing average high-low range) appearing during a DOWNTREND
signals a likely minor low forming (works 73% of the time per source's own
disclosed research using "Method 1": buy a penny above the tall candle's
high, cancelling if a lower low occurs first, with a stop below the lowest
of the three candles spanning day-before/tall-candle-day/day-after).

Distinct from prior tall-candle-FILTER strategies already tested in this
repo (On Neck 2026-09-21-168, Tweezers Bottom 2026-09-24-120), which use the
tall-candle criterion as a SECONDARY confirmation filter layered on a
DIFFERENT primary candlestick pattern. This strategy tests Bulkowski's tall
candle signal directly and standalone as the primary entry trigger, per his
own "Trading Minor Lows" rules, not mixed with another named pattern.

Downtrend context: close below its own trend_window-day SMA (source doesn't
give a fixed downtrend definition; we use a simple trailing SMA slope-below
filter as the mechanical proxy).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 long/flat)
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    candle_avg_window: int = 22,
    tall_candle_ratio: float = 1.46,
    trend_window: int = 50,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    candle_avg_window : lookback for the average high-low range (excludes
        today, per source's own methodology).
    tall_candle_ratio : today's high-low range must exceed this multiple of
        the trailing average to be a "tall candle" (source default 1.46,
        i.e. 146%).
    trend_window : SMA window used as the downtrend-context proxy (close
        below this SMA => downtrend).
    max_hold_days : time-stop backstop (source gives no explicit exit
        target beyond the initial stop; this repo adds a bounded holding
        period since a pure entry-only rule needs SOME exit for a
        continuous backtest).
    """
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]
    n = len(close)

    candle_range = high - low
    avg_range = candle_range.rolling(candle_avg_window).mean().shift(1)
    is_tall_candle = candle_range > (tall_candle_ratio * avg_range)

    sma = close.rolling(trend_window).mean()
    is_downtrend = close < sma

    # Structural stop: below the lowest of (day-before, tall-candle-day,
    # day-after). We approximate "day-after" confirmation by entering on
    # the day AFTER the tall candle (buy a penny above the tall candle's
    # high, simplified here to buying at the next day's close if that
    # close clears the tall candle's high -- a daily-bar-close
    # approximation of the source's own intraday buy-stop mechanics).
    tall_high = high.copy()
    stop_low = pd.concat([low.shift(1), low, low.shift(-1)], axis=1).min(axis=1)

    close_vals = close.values
    high_vals = high.values
    low_vals = low.values

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = -1
    stop_price = None

    pending_signal_idx = -1  # index of the tall-candle day awaiting next-day confirmation

    for i in range(n):
        if pending_signal_idx >= 0 and not in_position:
            confirm_i = pending_signal_idx
            # Cancel if a lower low occurred before confirmation (source's own rule)
            if low_vals[i] < low_vals[confirm_i] and i > confirm_i:
                pending_signal_idx = -1
            elif i == confirm_i + 1:
                # Buy a penny above the tall candle's high -> approximate with
                # entering if today's close clears that high.
                if close_vals[i] > high_vals[confirm_i]:
                    in_position = True
                    entry_idx = i
                    if not math.isnan(stop_low.iloc[confirm_i]):
                        stop_price = stop_low.iloc[confirm_i]
                    else:
                        stop_price = low_vals[confirm_i]
                pending_signal_idx = -1

        if not in_position and pending_signal_idx < 0:
            if bool(is_tall_candle.iloc[i]) and bool(is_downtrend.iloc[i]):
                pending_signal_idx = i

        if in_position:
            held_days = i - entry_idx
            stop_hit = stop_price is not None and close_vals[i] < stop_price
            time_stop_hit = held_days >= max_hold_days
            if stop_hit or time_stop_hit:
                in_position = False
                stop_price = None

        position.iloc[i] = 1 if in_position else 0

    return position.astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    candle_avg_window: int = 22,
    tall_candle_ratio: float = 1.46,
    trend_window: int = 50,
    max_hold_days: int = 20,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs here)."""
    df = _prep(price_df)
    close = df["close"]

    positions = generate_signals(
        price_df,
        candle_avg_window=candle_avg_window,
        tall_candle_ratio=tall_candle_ratio,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = positions.shift(1).fillna(0).astype(int) * daily_returns
    return strat_returns
